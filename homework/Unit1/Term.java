import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Iterator;

public class Term implements Branch {
    private ArrayList<Factor> factors;
    private boolean negative = false;
    private Poly contents = new Poly();
    private boolean simplified = false;

    public Term getCopy() {
        Term term = new Term();
        for (Factor factor : factors) {
            term.factors.add(factor.getCopy());
        }
        term.simplified = simplified;
        term.negative = negative;
        term.contents = contents.getCopy();
        return term;
    }

    public void negate() {
        negative = !negative;
    }

    public Poly getContents() {
        return contents;
    }

    public void simplify(FunctionPattern functionPattern) {
        if (simplified) {
            return;
        }
        contents = new Poly();
        Mono mono;
        if (negative) {
            mono = new Mono(BigInteger.ZERO, new BigInteger("-1"));
        }
        else {
            mono = new Mono(BigInteger.ZERO, BigInteger.ONE);
        }
        contents.addMono(mono);
        for (int i = 0; i < factors.size(); i++) {
            Factor factor = factors.get(i);
            if (factor instanceof Function) {
                factor.simplify(functionPattern);
                String functionName = ((Function) factor).getFunctionName();
                int functionNum = ((Function) factor).getFunctionNum();
                ArrayList<Factor> arguments = ((Function) factor).getCopy().getArguments();
                Expr expr = functionPattern.functionToExpr(functionName,functionNum,arguments);
                factor = expr;
                factors.set(i,expr);
            }
            factor.simplify(functionPattern);
            contents.mul(factor.getContents());
        }
        contents.mergeAll();
        simplified  = true;
    }

    public boolean isNegative() {
        return negative;
    }

    public Term() {
        this.factors = new ArrayList<>();
    }

    public void addFactor(Factor factor) {
        this.factors.add(factor);
    }

    public String toString() {
        Iterator<Factor> iter = factors.iterator();
        StringBuilder sb = new StringBuilder();
        sb.append(iter.next().toString());
        if (iter.hasNext()) {
            do {
                sb.append("*");
                sb.append(iter.next().toString());
            } while (iter.hasNext());
        }
        return sb.toString();
    }

    public void replacePow(String functionName,FunctionPattern functionPattern,
        ArrayList<Factor> arguments) {
        simplified = false;
        for (int i = 0; i < factors.size(); i++) {
            Factor factor = factors.get(i);
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
                factors.set(i,expr);
            }
            else if (factor instanceof Branch) {
                ((Branch) factor).replacePow(functionName,functionPattern, arguments);
            }
        }
    }
}
