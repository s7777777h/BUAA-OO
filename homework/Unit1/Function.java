import java.util.ArrayList;

public class Function implements Factor, Branch {
    private final Integer functionNum;
    private final ArrayList<Factor> arguments = new ArrayList<>();
    private Poly contents = new Poly();
    private boolean simplifed = false;
    private String functionName = null;

    public String getFunctionName() {
        return functionName;
    }

    public void replacePow(String functionName,FunctionPattern functionPattern,
        ArrayList<Factor> arguments) {
        simplifed = false;
        for (int i = 0; i < this.arguments.size(); i++) {
            Factor factor = this.arguments.get(i);
            if (factor instanceof Pow) {
                Expr expr = new Expr();
                Term term = new Term();
                if (((Pow) factor).getVarName().equals("x")) {
                    if (functionPattern.getVarNames(functionName).get(0).equals("x")) {
                        term.addFactor(arguments.get(0));
                    }
                    else {
                        term.addFactor(arguments.get(1));
                    }
                }
                else {
                    if (functionPattern.getVarNames(functionName).get(0).equals("x")) {
                        term.addFactor(arguments.get(1));
                    }
                    else {
                        term.addFactor(arguments.get(0));
                    }
                }
                expr.addTerm(term);
                expr.setExponent(((Pow) factor).getExponent());
                this.arguments.set(i,expr);
            }
            else if (factor instanceof Branch) {
                ((Branch) factor).replacePow(functionName,functionPattern, arguments);
            }
        }
    }

    public Integer getFunctionNum() {
        return functionNum;
    }

    public ArrayList<Factor> getArguments() {
        return arguments;
    }

    public void simplify(FunctionPattern functionPattern) {
        if (simplifed) {
            return;
        }
        contents = new Poly();
        for (Factor factor : arguments) {
            factor.simplify(functionPattern);
        }
        contents.mergeAll();
        simplifed = true;
    }

    public Function getCopy() {
        Function function = new Function(functionName,functionNum);
        function.simplifed = false;
        for (Factor argument : arguments) {
            function.addArgument(argument.getCopy());
        }
        function.contents = contents.getCopy();
        return function;
    }

    public Function(String functionName, Integer functionNum) {
        this.functionNum = functionNum;
        this.functionName = functionName;
    }

    public void addArgument(Factor argument) {
        arguments.add(argument);
    }

    public Poly getContents() {
        return contents;
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(functionName);
        if (functionName.equals("f")) {
            sb.append("{").append(functionNum).append("}");
        }
        sb.append("(");
        for (int i = 0; i < arguments.size(); i++) {
            sb.append(arguments.get(i).toString());
            if (i < arguments.size() - 1) {
                sb.append(",");
            }
        }
        sb.append(")");
        return sb.toString();
    }
}
