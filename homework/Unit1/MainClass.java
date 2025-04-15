import java.util.Scanner;

public class MainClass {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        Solver solver = new Solver(scanner);
        solver.solve();
    }
}
