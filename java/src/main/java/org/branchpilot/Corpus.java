package org.branchpilot;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.util.Printer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.*;
import java.util.regex.Pattern;

/** Offline transformation and context extraction from exactly one original classfile. */
public final class Corpus {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Pattern REFERENCE_TYPE = Pattern.compile("L[^;]+;");
    record Entry(Branches.Site site, boolean selected) {}
    record Context(String branch_id, String context, String masked_context, List<String> opcodes,
                   String method_hash) {}

    static List<Entry> readInventory(Path file) throws Exception {
        return List.of(JSON.readValue(file.toFile(), Entry[].class));
    }

    static void labels(List<Entry> entries, String workload, Path path) throws Exception {
        var labels = new ArrayList<Pilot.Label>();
        for (int i = 0; i < entries.size(); i++) {
            if (!entries.get(i).selected()) continue;
            long t = Counters.jumps(i), f = Counters.falls(i);
            Double p = t == 0 && f == 0 ? null : t / ((double) t + f);
            labels.add(new Pilot.Label("v0", entries.get(i).site().branch_id(), workload, t, f, p));
        }
        Pilot.jsonl(path, labels);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("CLASS METHOD_CSV WORKDIR OUTPUT");
        byte[] bytes = Files.readAllBytes(Path.of(args[0]));
        var methods = Set.of(args[1].split(","));
        Path work = Path.of(args[2]), output = Path.of(args[3]);
        var scan = Branches.scan(bytes, true);
        var tree = new ClassNode();
        new ClassReader(bytes).accept(tree, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
        if (!tree.methods.stream().map(m -> m.name).toList().containsAll(methods))
            throw new IllegalArgumentException("Missing requested method in " + tree.name);
        var entries = scan.sites().stream().map(s -> new Entry(s, methods.contains(s.method_name()))).toList();
        var selected = entries.stream().filter(Entry::selected).map(Entry::site).toList();
        if (selected.isEmpty()) throw new IllegalArgumentException("No selected conditional branches");
        var rewritten = work.resolve("patched").resolve(tree.name + ".class");
        Files.createDirectories(rewritten.getParent());
        Files.write(rewritten, scan.rewritten());
        JSON.writeValue(work.resolve("inventory.json").toFile(), entries);
        Pilot.jsonl(output.resolve("static.jsonl"), selected);
        Pilot.jsonl(output.resolve("context.jsonl"), contexts(tree, entries));
    }

    static List<Context> contexts(ClassNode tree, List<Entry> entries) throws Exception {
        var result = new ArrayList<Context>();
        int originalIndex = 0;
        for (int methodIndex = 0; methodIndex < tree.methods.size(); methodIndex++) {
            var method = tree.methods.get(methodIndex);
            var code = new ArrayList<AbstractInsnNode>();
            Map<LabelNode, Integer> destinations = new IdentityHashMap<>();
            for (var insn : method.instructions) {
                if (insn instanceof LabelNode label) destinations.put(label, code.size());
                if (insn.getOpcode() >= 0) code.add(insn);
            }
            var opcodes = code.stream().map(n -> Printer.OPCODES[n.getOpcode()]).toList();
            var hash = MessageDigest.getInstance("SHA-256").digest(String.join(" ", opcodes).getBytes(StandardCharsets.US_ASCII));
            for (int i = 0; i < code.size(); i++) {
                if (!opcodes.get(i).startsWith("IF")) continue;
                Entry entry = entries.get(originalIndex++);
                if (entry.site.method_index() != methodIndex || !opcodes.get(i).equals(entry.site.branch_opcode()))
                    throw new IllegalStateException("Original instruction and branch inventory differ");
                if (!entry.selected) continue;
                var named = new ArrayList<String>();
                var masked = new ArrayList<String>();
                int begin = Math.max(0, i - 5), end = Math.min(code.size(), i + 6);
                for (int j = begin; j < end; j++) {
                    String prefix = (i == j ? ">> " : "   ") + opcodes.get(j);
                    named.add(prefix + operand(code.get(j), j, destinations, false));
                    masked.add(prefix + operand(code.get(j), j, destinations, true));
                }
                result.add(new Context(entry.site.branch_id(), String.join("\n", named), String.join("\n", masked),
                        opcodes.subList(begin, end), HexFormat.of().formatHex(hash)));
            }
        }
        if (originalIndex != entries.size()) throw new IllegalStateException("Inventory length mismatch");
        return result;
    }

    private static String descriptor(String desc, boolean mask) {
        return mask ? REFERENCE_TYPE.matcher(desc).replaceAll("LTYPE;") : desc;
    }

    private static String operand(AbstractInsnNode insn, int i, Map<LabelNode,Integer> dest, boolean mask) {
        return switch (insn) {
            case JumpInsnNode j -> " jump=" + (dest.get(j.label) - i);
            case MethodInsnNode m -> " " + (mask ? "TYPE.member" : m.owner + "." + m.name) + descriptor(m.desc, mask);
            case FieldInsnNode f -> " " + (mask ? "TYPE.field" : f.owner + "." + f.name) + " " + descriptor(f.desc, mask);
            case TypeInsnNode t -> " " + (mask ? "TYPE" : t.desc);
            case InvokeDynamicInsnNode d -> " " + (mask ? "member" : d.name) + descriptor(d.desc, mask);
            case MultiANewArrayInsnNode a -> " " + descriptor(a.desc, mask) + " dims=" + a.dims;
            case LdcInsnNode l -> " " + (l.cst instanceof Number ? l.cst : "<constant>");
            case VarInsnNode v -> " slot=" + v.var;
            case IincInsnNode n -> " slot=" + n.var + " by=" + n.incr;
            case IntInsnNode n -> " " + n.operand;
            case TableSwitchInsnNode s -> " cases=" + s.labels.size();
            case LookupSwitchInsnNode s -> " cases=" + s.keys.size();
            default -> "";
        };
    }
}
