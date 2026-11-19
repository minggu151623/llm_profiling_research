package org.branchpilot;

import static org.junit.jupiter.api.Assertions.*;
import static org.objectweb.asm.Opcodes.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Label;

class CorpusVerificationTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Path CORPUS = Path.of("../experiments/study/corpus");

    // Two conditional jumps and a separate unconditional edge reach exactly the same label.
    private static byte[] sharedTargetClass() {
        var writer = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
        writer.visit(V25, ACC_PUBLIC, "fixture/SharedTarget", null, "java/lang/Object", null);
        var method = writer.visitMethod(ACC_PUBLIC | ACC_STATIC, "score", "(II)I", null, null);
        var accept = new Label();
        var reject = new Label();
        method.visitCode();
        method.visitVarInsn(ILOAD, 0);
        method.visitJumpInsn(IFLT, accept);
        method.visitVarInsn(ILOAD, 1);
        method.visitJumpInsn(IFEQ, accept);
        method.visitVarInsn(ILOAD, 0);
        method.visitIntInsn(BIPUSH, 7);
        method.visitJumpInsn(IF_ICMPNE, reject);
        method.visitJumpInsn(GOTO, accept);
        method.visitLabel(accept);
        method.visitInsn(ICONST_1);
        method.visitInsn(IRETURN);
        method.visitLabel(reject);
        method.visitInsn(ICONST_M1);
        method.visitInsn(IRETURN);
        method.visitMaxs(0, 0);
        method.visitEnd();
        writer.visitEnd();
        return writer.toByteArray();
    }

    @Test void sharedTargetCountsEachSourceEdgeExactlyOnce() throws Exception {
        byte[] bytes = sharedTargetClass();
        var original = Pilot.load(bytes).getMethod("score", int.class, int.class);
        var scan = Branches.scan(bytes, true);
        var traced = Pilot.load(scan.rewritten()).getMethod("score", int.class, int.class);
        assertEquals(List.of(1, 5, 11), scan.sites().stream().map(Branches.Site::original_bci).toList());
        assertEquals(List.of(17, 17, 19), scan.sites().stream().map(Branches.Site::target_bci).toList());
        Counters.start(3);
        for (int[] pair : List.of(new int[]{-2,7}, new int[]{-1,0}, new int[]{2,0},
                                  new int[]{7,3}, new int[]{0,3}, new int[]{2,9})) {
            int x = pair[0], y = pair[1];
            int expected = x < 0 || y == 0 || x == 7 ? 1 : -1;
            assertEquals(expected, original.invoke(null, x, y));
            assertEquals(expected, traced.invoke(null, x, y));
        }
        assertArrayEquals(new long[]{2,1,2}, new long[]{Counters.jumps(0),Counters.jumps(1),Counters.jumps(2)});
        assertArrayEquals(new long[]{4,3,1}, new long[]{Counters.falls(0),Counters.falls(1),Counters.falls(2)});
    }

    private static Map<String, JsonNode> rows(Path file) throws Exception {
        var result = new HashMap<String, JsonNode>();
        for (String line : Files.readAllLines(file)) {
            JsonNode row = JSON.readTree(line);
            String id = row.required("branch_id").textValue();
            assertNull(result.put(id, row), "Duplicate " + id);
        }
        return result;
    }

    @Test void aWidenedProductOracleMatchesBothRecordedJodaWorkloads() throws Exception {
        Path project = CORPUS.resolve("joda-time");
        var staticRows = rows(project.resolve("static.jsonl"));
        var site = staticRows.values().stream().filter(r -> r.get("method_name").asText().equals("safeMultiply")
                && r.get("method_descriptor").asText().equals("(II)I") && r.get("original_bci").asInt() == 19)
                .findFirst().orElseThrow();
        assertEquals("IFLE", site.required("branch_opcode").textValue());
        for (String workload : List.of("normal", "shift")) {
            int limit = workload.equals("normal") ? 17 : 3;
            var random = new Random(1516);
            int bounded = 0;
            for (int i = 0; i < 100; i++) {
                int k = random.nextInt(6);
                long n = i % 20 < limit ? k + 1 : new long[]{-93, -1, 0, 31, 99999, 100000}[k];
                if (n * n <= Integer.MAX_VALUE) bounded++;
            }
            var label = rows(project.resolve(workload + ".jsonl")).get(site.required("branch_id").asText());
            assertEquals(bounded, label.required("taken_count").longValue());
            assertEquals(100 - bounded, label.required("fallthrough_count").longValue());
        }
    }

    @Test void corpusContextsHaveAlignedFocalInstructionsAndDisjointLabelFields() throws Exception {
        var projects = JSON.readTree(Path.of("../experiments/configs/corpus.json").toFile()).required("projects");
        for (var project : projects) {
            Path dir = CORPUS.resolve(project.required("project").asText());
            var staticRows = rows(dir.resolve("static.jsonl"));
            var contexts = rows(dir.resolve("context.jsonl"));
            assertEquals(staticRows.keySet(), contexts.keySet());
            for (var entry : contexts.entrySet()) {
                var row = entry.getValue();
                List<String> named = row.required("context").asText().lines().toList();
                List<String> masked = row.required("masked_context").asText().lines().toList();
                var opcodes = row.required("opcodes");
                assertTrue(named.size() >= 1 && named.size() <= 11);
                assertEquals(named.size(), masked.size());
                assertEquals(named.size(), opcodes.size());
                int focal = 0;
                for (int i = 0; i < named.size(); i++) {
                    String opcode = opcodes.get(i).textValue();
                    String prefix = named.get(i).startsWith(">> ") ? ">> " : "   ";
                    assertEquals(opcode, named.get(i).substring(3).split(" ", 2)[0]);
                    assertEquals(opcode, masked.get(i).substring(3).split(" ", 2)[0]);
                    assertTrue(masked.get(i).startsWith(prefix));
                    if (prefix.equals(">> ")) {
                        focal++;
                        assertEquals(staticRows.get(entry.getKey()).required("branch_opcode").asText(), opcode);
                    }
                }
                assertEquals(1, focal);
                assertTrue(row.required("method_hash").asText().matches("[a-f0-9]{64}"));
                for (String key : List.of("p_taken", "taken_count", "fallthrough_count", "workload_id")) {
                    assertFalse(row.has(key));
                    assertFalse(staticRows.get(entry.getKey()).has(key));
                }
            }
        }
    }
}
