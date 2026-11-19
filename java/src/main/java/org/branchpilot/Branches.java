package org.branchpilot;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import org.objectweb.asm.*;
import org.objectweb.asm.util.Printer;

final class Branches {
    record Site(String schema_version, String branch_id, String artifact_sha256, String class_name,
                int method_index, String method_name, String method_descriptor, int original_bci,
                String branch_opcode, int target_bci, int fallthrough_bci) {}
    record Scan(List<Site> sites, byte[] rewritten) {}

    // The reader reports offsets in the original method's Code array, before visitor edits.
    private static final class OffsetReader extends ClassReader {
        private final Map<Label, Integer> targets = new IdentityHashMap<>();
        private int bci;

        OffsetReader(byte[] bytes) { super(bytes); }

        @Override protected void readBytecodeInstructionOffset(int offset) { bci = offset; }

        @Override protected Label readLabel(int offset, Label[] labels) {
            Label label = super.readLabel(offset, labels);
            targets.put(label, offset);
            return label;
        }
    }

    static Scan scan(byte[] original, boolean instrument) throws NoSuchAlgorithmException {
        String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original));
        var reader = new OffsetReader(original);
        var writer = instrument ? new ClassWriter(reader, ClassWriter.COMPUTE_FRAMES) : null;
        var sites = new ArrayList<Site>();
        reader.accept(new ClassVisitor(Opcodes.ASM9, writer) {
            int methodCount;

            @Override public MethodVisitor visitMethod(int access, String name, String descriptor,
                                                      String signature, String[] exceptions) {
                int method = methodCount++;
                var downstream = super.visitMethod(access, name, descriptor, signature, exceptions);
                return new MethodVisitor(Opcodes.ASM9, downstream) {
                    @Override public void visitJumpInsn(int opcode, Label target) {
                        boolean binary = (opcode >= Opcodes.IFEQ && opcode <= Opcodes.IF_ACMPNE)
                                || opcode == Opcodes.IFNULL || opcode == Opcodes.IFNONNULL;
                        if (!binary) {
                            super.visitJumpInsn(opcode, target);
                            return;
                        }
                        int bci = reader.bci;
                        int index = sites.size();
                        sites.add(new Site("v0", sha + ":" + method + ":" + bci, sha,
                                reader.getClassName(), method, name, descriptor, bci,
                                Printer.OPCODES[opcode], reader.targets.get(target), bci + 3));
                        if (instrument) {
                            Label taken = new Label();
                            Label next = new Label();
                            super.visitJumpInsn(opcode, taken);
                            probe(index, "fallthrough");
                            super.visitJumpInsn(Opcodes.GOTO, next);
                            super.visitLabel(taken);
                            probe(index, "taken");
                            super.visitJumpInsn(Opcodes.GOTO, target);
                            super.visitLabel(next);
                        }
                    }

                    private void probe(int index, String edge) {
                        super.visitLdcInsn(index);
                        super.visitMethodInsn(Opcodes.INVOKESTATIC, "org/branchpilot/Counters",
                                              edge, "(I)V", false);
                    }
                };
            }
        }, ClassReader.SKIP_FRAMES);
        return new Scan(List.copyOf(sites), instrument ? writer.toByteArray() : null);
    }
}
