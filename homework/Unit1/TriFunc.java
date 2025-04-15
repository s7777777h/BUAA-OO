import java.math.BigInteger;
import java.util.ArrayList;

public class TriFunc implements Factor, Branch {
    // trigonometric function factor
    private final boolean type;
    private Factor factor;
    private BigInteger exponent;
    private Poly contents = new Poly();
    private boolean simplified;
    //type=1:sine
    //type=0:cosine

    public TriFunc getCopy() {
        TriFunc triFunc = new TriFunc(type, factor.getCopy(), exponent);
        triFunc.contents = contents.getCopy();
        triFunc.simplified = simplified;
        return triFunc;
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        if (type) {
            sb.append("sin(");
        }
        else {
            sb.append("cos(");
        }
        sb.append(factor);
        sb.append(")");
        if (!exponent.equals(BigInteger.ONE)) {
            sb.append("^");
            sb.append(exponent);
        }
        return sb.toString();
    }

    TriFunc(boolean type,Factor factor,BigInteger exponent) {
        this.type = type;
        this.factor = factor;
        this.exponent = exponent;
    }

    public Poly getContents() {
        return contents;
    }

    public void replacePow(String functionName,FunctionPattern functionPattern,
        ArrayList<Factor> arguments) {
        simplified = false;
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
            factor = expr;
        }
        else if (factor instanceof Branch) {
            ((Branch) factor).replacePow(functionName,functionPattern, arguments);
        }
    }

    public void simplify(FunctionPattern functionPattern) {
        if (simplified) {
            return;
        }
        contents = new Poly();
        if (exponent.equals(BigInteger.ZERO)) {
            contents.addMono(new Mono(BigInteger.ZERO,BigInteger.ONE));
            return;
        }
        if (factor instanceof Function) {
            factor.simplify(functionPattern);
            String functionName = ((Function) factor).getFunctionName();
            int functionNum = ((Function) factor).getFunctionNum();
            ArrayList<Factor> arguments = ((Function) factor).getArguments();
            Expr expr = functionPattern.functionToExpr(functionName,functionNum,arguments);
            factor = expr;
        }
        factor.simplify(functionPattern);
        Mono mono = new Mono(BigInteger.ZERO, BigInteger.ONE);
        if (factor.getContents().equalsToZero()) {
            if (type) {
                mono = new Mono(BigInteger.ZERO, BigInteger.ZERO);
            }
            else {
                mono = new Mono(BigInteger.ZERO, BigInteger.ONE);
            }
            contents.clear();
            contents.addMono(mono);
            return;
        }
        if (type) {
            mono.addSin(factor, exponent);
        }
        else {
            mono.addCos(factor, exponent);
        }
        contents.addMono(mono);
        contents.mergeAll();
    }
}
