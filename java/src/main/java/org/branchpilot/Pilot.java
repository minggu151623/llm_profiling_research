package org.branchpilot;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

public final class Pilot {
    private static final ObjectMapper JSON = new ObjectMapper();
    record Label(String schema_version, String branch_id, String workload_id,
                 long taken_count, long fallthrough_count, Double p_taken) {}

    static void jsonl(Path path, List<?> rows) throws Exception {
        try (BufferedWriter out = Files.newBufferedWriter(path)) {
            for (var row : rows) {
                out.write(JSON.writeValueAsString(row));
                out.newLine();
            }
        }
    }

    static Class<?> load(byte[] bytes) {
        class FixtureLoader extends ClassLoader {
            Class<?> define() { return defineClass(null, bytes, 0, bytes.length); }
        }
        return new FixtureLoader().define();
    }

    private static int score(byte[] bytes, int[] inputs) throws Exception {
        return (int) load(bytes).getMethod("score", int[].class).invoke(null, (Object) inputs.clone());
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 3 && args[0].equals("extract")) {
            var scan = Branches.scan(Files.readAllBytes(Path.of(args[1])), false);
            jsonl(Path.of(args[2]), scan.sites());
            return;
        }
        if (args.length != 5 || !args[0].equals("profile")) {
            throw new IllegalArgumentException("extract CLASS STATIC.jsonl | profile CLASS CONFIG WORKLOAD LABELS.jsonl");
        }
        byte[] original = Files.readAllBytes(Path.of(args[1]));
        var config = JSON.readTree(Path.of(args[2]).toFile());
        String workload = args[3];
        var values = new ArrayList<Integer>();
        config.required("workloads").required(workload).forEach(n -> values.add(n.intValue()));
        Collections.shuffle(values, new Random(config.required("seed").longValue()));
        int[] inputs = values.stream().mapToInt(Integer::intValue).toArray();
        int reference = score(original, inputs);
        var scan = Branches.scan(original, true);
        Counters.start(scan.sites().size());
        int measured = score(scan.rewritten(), inputs);
        if (reference != measured) throw new IllegalStateException("Original and instrumented results differ");
        var labels = new ArrayList<Label>();
        for (int i = 0; i < scan.sites().size(); i++) {
            long t = Counters.jumps(i);
            long f = Counters.falls(i);
            Double p = t == 0 && f == 0 ? null : t / ((double) t + f);
            labels.add(new Label("v0", scan.sites().get(i).branch_id(), workload, t, f, p));
        }
        jsonl(Path.of(args[4]), labels);
        System.out.printf("%s original_score=%d instrumented_score=%d%n", workload, reference, measured);
    }
}
