package org.branchpilot;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Random;

import com.google.common.base.Ascii;
import com.squareup.javapoet.CodeBlock;
import org.apache.commons.codec.language.Soundex;
import org.apache.maven.artifact.versioning.ComparableVersion;
import org.joda.time.field.FieldUtils;
import org.json.JSONObject;
import org.jsoup.internal.StringUtil;
import org.locationtech.jts.geom.Envelope;

/** Each workload invokes public library APIs. The JVM classpath controls instrumentation. */
public final class Workloads {
    private static final String[] NAMES = {"Jackson", "Smith", "Walker", "Ramirez", "Tran", "Miller"};
    private static final String[] ODD_NAMES = {"Hwhwhw", "Bbbbbb", "", "----", "Q", "Ash-craft"};
    private static final String[] WORDS = {"green", "river", "paper", "train", "strawberry", "time"};
    private static final String[] CASES = {"McQueen", "ASCII", "L3tter", "", "Café", "0_W"};
    private static final String[] RELEASE = {"1.0", "2.1.3", "5", "2.0.1", "1.2", "1.0.2"};
    private static final String[] PRERELEASE = {"1.02-alpha-3", "4.0.0-RC1", "1-000000000000004",
            "2.3beta.4", "5.0.0-final", "0.000000000000000000000000000001-snapshot"};
    private static final String[] TEXT = {"green hills", "Hello", "one two three", "Java 25", "abc", "morning"};
    private static final String[] WHITESPACE = {" \t\n\r", "a    b\tc\r\nd", "\u200Bx\u00A0  y", "", "  🌱  ", " \u00AD \u200B "};
    private static final String[] JSON = {"{\"v\":\"red\"}", "{\"v\":\"abc\"}", "{\"v\":\"map\"}",
            "{\"v\":\"2\"}", "{\"v\":\"\"}", "{\"v\":\"cat\"}"};
    private static final String[] MORE_JSON = {"{\n \"v\" : \"a\\nb\\tc\"\n}", "{\"a\":[true,false,null],\"v\":\"x\"}",
            "{\r\n \"v\":\"\\u0041\\u0032\"}", "{\"x\":-12.5e2,\"v\":\"\\\\\"}",
            "{\"v\":\"line\\r\\n\" , \"n\": 3 }", "{ \"o\":{\"k\":1}, \"v\":\"\\\"\" }"};
    private static final String[] LITERALS = {"green hills", "Hello", "42", "abc", "Z", "Morning"};
    private static final String[] ESCAPES = {"\"q\"\\", "\nnew\nline", "\u0001\u0002", "a\t\fb", "'\r", "🌱\n\t"};

    private static String sample(String project, boolean familyA, int index) {
        switch (project) {
            case "commons-codec": {
                String s = (familyA ? NAMES : ODD_NAMES)[index];
                return new Soundex().soundex(s);
            }
            case "guava": {
                String s = (familyA ? WORDS : CASES)[index];
                String pair = familyA ? new String(s) : switch (index % 3) {
                    case 0 -> s.toUpperCase(java.util.Locale.ROOT);
                    case 1 -> s + "a";
                    default -> "!" + s.substring(Math.min(1, s.length()));
                };
                return Ascii.toLowerCase(s) + "/" + Ascii.toUpperCase(s) + "/" + Ascii.equalsIgnoreCase(s, pair);
            }
            case "joda-time": {
                int n = familyA ? index + 1 : new int[]{-93, -1, 0, 31, 99999, 100000}[index];
                String product;
                try {
                    product = Integer.toString(FieldUtils.safeMultiply(n, n));
                } catch (ArithmeticException e) {
                    product = e.getClass().getName();
                }
                return product + "/" + FieldUtils.safeAdd(n, 9) + "/" + FieldUtils.safeToInt((long) n)
                        + "/" + FieldUtils.getWrappedValue(n, 0, 30);
            }
            case "maven-artifact": {
                String[] versions = familyA ? RELEASE : PRERELEASE;
                var a = new ComparableVersion(versions[index]);
                var b = new ComparableVersion(versions[(index + 1) % versions.length]);
                return a.getCanonical() + "/" + Integer.signum(a.compareTo(b));
            }
            case "jsoup": {
                String s = (familyA ? TEXT : WHITESPACE)[index];
                return StringUtil.isBlank(s) + "/" + StringUtil.normaliseWhitespace(s);
            }
            case "org-json": {
                String s = (familyA ? JSON : MORE_JSON)[index];
                return new JSONObject(s).getString("v");
            }
            case "javapoet": {
                String s = (familyA ? LITERALS : ESCAPES)[index];
                return CodeBlock.of("$S", s).toString();
            }
            case "jts": {
                var a = new Envelope(0, 10, 0, 10);
                double x = familyA ? index : switch(index % 3) {
                    case 0 -> -8 - index;
                    case 1 -> 11 + index;
                    default -> 6 + index;
                };
                double y = familyA ? 8 - index : index * 3 - 2;
                var b = new Envelope(x, x + 2, y, y + 3);
                return a.intersects(b) + "/" + a.covers(x, y) + "/" + a.distance(b) + "/" + a.intersection(b);
            }
            default: throw new IllegalArgumentException("Unknown project " + project);
        }
    }

    public static void main(String[] args) throws Exception {
        // Arguments: project seed examples period familyAWithinPeriod inventory labels-or-dash workload.
        var sites = Corpus.readInventory(java.nio.file.Path.of(args[5]));
        Counters.start(sites.size());
        var random = new Random(Long.parseLong(args[1]));
        int period = Integer.parseInt(args[3]);
        int familyALimit = Integer.parseInt(args[4]);
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (int i = 0; i < Integer.parseInt(args[2]); i++) {
            String result = sample(args[0], i % period < familyALimit, random.nextInt(6));
            byte[] bytes = result.getBytes(StandardCharsets.UTF_8);
            digest.update(ByteBuffer.allocate(4).putInt(bytes.length).array());
            digest.update(bytes);
        }
        if (!args[6].equals("-")) Corpus.labels(sites, args[7], java.nio.file.Path.of(args[6]));
        System.out.println(HexFormat.of().formatHex(digest.digest()));
    }
}
