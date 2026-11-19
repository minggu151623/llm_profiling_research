package org.branchpilot;

import java.util.concurrent.atomic.AtomicLongArray;

public final class Counters {
    private static AtomicLongArray jumps;
    private static AtomicLongArray falls;

    // The pilot runs one workload per fresh JVM. Workers must finish before counts are read.
    static void start(int size) {
        jumps = new AtomicLongArray(size);
        falls = new AtomicLongArray(size);
    }

    public static void taken(int i) { jumps.getAndUpdate(i, Math::incrementExact); }
    public static void fallthrough(int i) { falls.getAndUpdate(i, Math::incrementExact); }
    static long jumps(int i) { return jumps.get(i); }
    static long falls(int i) { return falls.get(i); }
}
