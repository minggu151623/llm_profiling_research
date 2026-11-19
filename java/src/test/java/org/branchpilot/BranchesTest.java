package org.branchpilot;

import static org.junit.jupiter.api.Assertions.*;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import javax.tools.ToolProvider;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class BranchesTest {
    @TempDir Path tmp;

    private Path compileFixture() {
        assertEquals(0, ToolProvider.getSystemJavaCompiler().run(null, null, null,
                "--release", "25", "-d", tmp.toString(), "fixtures/Decisions.java"));
        return tmp.resolve("fixture/Decisions.class");
    }

    @Test void inventoryMatchesOriginalJavap() throws Exception {
        Path file = compileFixture();
        byte[] bytes = Files.readAllBytes(file);
        var scan = Branches.scan(bytes, false);
        assertEquals(scan.sites(), Branches.scan(bytes, true).sites());
        var output = new StringWriter();
        var javap = java.util.spi.ToolProvider.findFirst("javap").orElseThrow();
        assertEquals(0, javap.run(new PrintWriter(output), new PrintWriter(System.err),
                                  "-c", "-s", file.toString()));
        var header = Pattern.compile("public (?:static )?[^ ]+ (\\w+)\\(.*");
        var conditional = Pattern.compile("(\\d+):\\s+(if\\w+)\\s+(\\d+)");
        String method = "", descriptor = "";
        var expected = new ArrayList<String>();
        for (String line : output.toString().lines().map(String::strip).toList()) {
            var h = header.matcher(line);
            if (h.matches()) method = h.group(1);
            if (line.startsWith("descriptor: ")) descriptor = line.substring(12);
            var i = conditional.matcher(line);
            if (i.matches()) expected.add(String.join(" ", method, descriptor, i.group(1), i.group(2), i.group(3)));
        }
        assertFalse(expected.isEmpty());
        assertEquals(expected, scan.sites().stream().map(s -> String.join(" ", s.method_name(),
                s.method_descriptor(), String.valueOf(s.original_bci()), s.branch_opcode().toLowerCase(java.util.Locale.ROOT),
                String.valueOf(s.target_bci()))).toList());
    }

    @Test void rewrittenClassRetainsBehaviorAndCountsJumpDirection() throws Exception {
        byte[] bytes = Files.readAllBytes(compileFixture());
        var scan = Branches.scan(bytes, true);
        var original = Pilot.load(bytes).getMethod("score", int[].class);
        var traced = Pilot.load(scan.rewritten()).getMethod("score", int[].class);
        Counters.start(scan.sites().size());
        for (int[] values : List.of(new int[]{}, new int[]{-2, -2, 0, 1, 4, 8})) {
            assertEquals(original.invoke(null, (Object) values), traced.invoke(null, (Object) values));
        }
        int guard = -1;
        for (int i = 0; i < scan.sites().size(); i++) {
            var site = scan.sites().get(i);
            if (site.method_name().equals("guard")) {
                assertEquals("IFGE", site.branch_opcode());
                guard = i;
            }
            if (site.method_name().equals("dormant")) {
                assertEquals(0, Counters.jumps(i));
                assertEquals(0, Counters.falls(i));
            }
        }
        assertTrue(guard >= 0);
        assertEquals(4, Counters.jumps(guard));
        assertEquals(2, Counters.falls(guard));
        var before = assertThrows(java.lang.reflect.InvocationTargetException.class,
                                  () -> original.invoke(null, (Object) null));
        var after = assertThrows(java.lang.reflect.InvocationTargetException.class,
                                 () -> traced.invoke(null, (Object) null));
        assertEquals(before.getCause().getClass(), after.getCause().getClass());
    }
}
