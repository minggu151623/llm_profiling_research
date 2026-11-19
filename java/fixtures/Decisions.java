package fixture;

public class Decisions {
    public static int guard(int n) {
        if (n < 0) return -1;
        return 1;
    }

    public static int score(int[] input) {
        int sum = 0;
        for (int n : input) {
            sum += guard(n);
            if ((n > 0 && n < 5) || n == -2) sum += 10;
            try {
                sum += 12 / n;
            } catch (ArithmeticException e) {
                sum -= 3;
            }
            sum += switch (n) {
                case -2 -> 2;
                case 0 -> 3;
                case 4 -> 4;
                default -> 1;
            };
        }
        return sum;
    }

    public static boolean dormant(int n) {
        return n == 42;
    }
}
