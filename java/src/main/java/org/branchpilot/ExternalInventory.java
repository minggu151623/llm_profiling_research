package org.branchpilot;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.ClassNode;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.*;
import java.util.jar.JarFile;

public final class ExternalInventory {
    record Candidate(Branches.Site site, String rank) {}

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("TARGET_JAR PACKAGE_PREFIX OUTPUT");
        Path output = Path.of(args[2]);
        Files.createDirectories(output.resolve("patched"));
        var hash = MessageDigest.getInstance("SHA-256");
        var candidates = new ArrayList<Candidate>();
        var slots = new HashMap<String,Integer>();
        var sampled = new ArrayList<Branches.Site>();
        var contexts = new ArrayList<Corpus.Context>();
        var originals = new ArrayList<String>();
        try (var jar = new JarFile(args[0])) {
            var names = jar.stream().map(e -> e.getName())
                    .filter(n -> n.startsWith(args[1]) && n.endsWith(".class")).sorted().toList();
            for (var name : names) {
                byte[] bytes = jar.getInputStream(jar.getJarEntry(name)).readAllBytes();
                for (var site : Branches.scan(bytes, false).sites()) {
                    var key = ("42:" + site.branch_id()).getBytes(StandardCharsets.UTF_8);
                    candidates.add(new Candidate(site, HexFormat.of().formatHex(hash.digest(key))));
                }
            }
            candidates.sort(Comparator.comparing(Candidate::rank));
            for (var candidate : candidates.stream().limit(96).toList()) {
                var site = candidate.site();
                slots.put(site.branch_id(), sampled.size());
                sampled.add(site);
            }
            if (sampled.isEmpty()) throw new IllegalStateException("Empty package " + args[1]);
            for (String name : sampled.stream().map(Branches.Site::class_name).distinct().sorted().toList()) {
                byte[] bytes = jar.getInputStream(jar.getJarEntry(name + ".class")).readAllBytes();
                var sites = Branches.scan(bytes, false).sites();
                int[] indices = sites.stream().mapToInt(s -> slots.getOrDefault(s.branch_id(), -1)).toArray();
                byte[] patched = Branches.scan(bytes, true, indices).rewritten();
                Path target = output.resolve("patched").resolve(name + ".class");
                Files.createDirectories(target.getParent());
                Files.write(target, patched);
                originals.add(name + "\t" + sites.get(0).artifact_sha256());
                var tree = new ClassNode();
                new ClassReader(bytes).accept(tree, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
                contexts.addAll(Corpus.contexts(tree, sites.stream()
                        .map(s -> new Corpus.Entry(s, slots.containsKey(s.branch_id()))).toList()));
            }
            new ObjectMapper().writeValue(output.resolve("population.json").toFile(), Map.of(
                    "classes_in_package", names.size(), "eligible_sites", candidates.size(),
                    "eligible_backward", candidates.stream().filter(c -> c.site.target_bci() < c.site.original_bci()).count(),
                    "selected_sites", sampled.size(), "selected_classes", originals.size()));
        }
        Files.write(output.resolve("classes.tsv"), originals);
        Pilot.jsonl(output.resolve("static.jsonl"), sampled);
        Pilot.jsonl(output.resolve("context.jsonl"), contexts);
    }
}
