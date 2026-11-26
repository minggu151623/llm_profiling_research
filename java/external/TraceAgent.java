package org.branchpilot;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.security.ProtectionDomain;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/** Count a preselected static inventory, including classes loaded by the benchmark's child loader. */
public final class TraceAgent {
    public static void premain(String arg, Instrumentation instrumentation) throws Exception {
        final Path out = Paths.get(arg);
        final Path inventory = Paths.get(System.getProperty("branchpilot.inventory"));
        final Map<String,String> digests = new HashMap<>();
        for (String row : Files.readAllLines(inventory.resolve("classes.tsv"))) {
            String[] fields = row.split("\t");
            digests.put(fields[0], fields[1]);
        }
        final int size = Files.readAllLines(inventory.resolve("static.jsonl")).size();
        Counters.start(size);
        final Set<String> loaded = ConcurrentHashMap.newKeySet();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                List<String> rows = new ArrayList<>();
                for (int i = 0; i < size; ++i) rows.add(Counters.jumps(i) + "," + Counters.falls(i));
                Files.write(out.resolve("counts.csv"), rows, StandardCharsets.UTF_8);
                Files.write(out.resolve("loaded.txt"), new TreeSet<>(loaded), StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        }));
        instrumentation.addTransformer(new ClassFileTransformer() {
            @Override public byte[] transform(ClassLoader loader, String name, Class<?> redef,
                                               ProtectionDomain domain, byte[] original) {
                if (!digests.containsKey(name)) return null;
                try {
                    byte[] sha = MessageDigest.getInstance("SHA-256").digest(original);
                    StringBuilder hex = new StringBuilder();
                    for (byte b : sha) hex.append(String.format("%02x", b & 255));
                    if (!digests.get(name).contentEquals(hex)) throw new IOException("Class digest mismatch: " + name);
                    byte[] patched = Files.readAllBytes(inventory.resolve("patched").resolve(name + ".class"));
                    loaded.add(name);
                    return patched;
                } catch (Exception e) {
                    e.printStackTrace();
                    Runtime.getRuntime().halt(4);
                    return null;
                }
            }
        });
    }
}
