import java.util.Scanner;

public class Solver {
    private final Scanner sc;
    private FunctionPattern functionPattern = new FunctionPattern();
    private String input;

    public Solver(Scanner sc) {
        this.sc = sc;
    }

    public void solve() {
        getFunctions();
        Lexer lexer = new Lexer(input);
        Parser parser = new Parser(lexer,functionPattern);
        Expr expr = parser.parseExpr();
        expr.simplify(functionPattern);
        expr.getContents().print();
    }

    private int getDepth(String s) {
        int depth = 0;
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) == 'f') {
                depth = Integer.max(depth,s.charAt(i + 2) - '0');
            }
        }
        return depth;
    }

    private void getFunctions() {
        input = sc.nextLine();
        String temp1;
        String functiong = null;
        String functionh = null;
        int t = Integer.parseInt(input);
        for (int i = 0; i < t; i++) {
            temp1 = preprocess(sc.nextLine());
            if (temp1.charAt(0) == 'g') {
                functiong = temp1;
            }
            else {
                functionh = temp1;
            }
        }
        input = sc.nextLine();
        if (input.charAt(0) == '1') {
            String function0 = preprocess(sc.nextLine());
            String function1 = preprocess(sc.nextLine());
            String functionn = preprocess(sc.nextLine());
            if (function0.charAt(2) == 'n') {
                String temp = function0;
                function0 = functionn;
                functionn = temp;
            }
            if (function1.charAt(2) == 'n') {
                String temp = function1;
                function1 = functionn;
                functionn = temp;
            }
            if (function0.charAt(2) == '1') {
                String temp = function0;
                function0 = function1;
                function1 = temp;
            }
            functionPattern.setFunction1(function1);
            functionPattern.setFunction0(function0);
            functionPattern.setFunctionn(functionn);
            input = preprocess(sc.nextLine());
            functionPattern.setDepth(getDepth(input));
        }
        else {
            input = preprocess(sc.nextLine());
        }
        if (functionh != null) {
            functionPattern.setFunctionh(functionh);
        }
        if (functiong != null) {
            functionPattern.setFunctiong(functiong);
        }
        functionPattern.processFunction();
    }

    private String preprocess(String input) {
        String result;
        result = input.replaceAll("[ \\t]","");
        result = result.replaceAll("(\\+{2})|(-{2})|(\\+{3})|(-\\+-)|(\\+-{2})|(-{2}\\+)","+");
        result = result.replaceAll("(\\+-)|(-\\+)|(-{3})|(-\\+{2})|(\\+{2}-)|(\\+-\\+)","-");
        return result;
    }
}
