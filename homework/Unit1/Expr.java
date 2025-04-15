import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Iterator;

public class Expr implements Factor, Branch {
    private ArrayList<Term> terms;
    private BigInteger exponent = BigInteger.ONE;
    private Poly contents = new Poly();
    private boolean simplified = false;

    public Expr getCopy() {
        Expr expr = new Expr();
        for (Term term : terms) {
            expr.addTerm(term.getCopy());
        }
        expr.setExponent(exponent);
        expr.contents = contents.getCopy();
        expr.simplified = simplified;
        return expr;
    }

    public Poly getContents() {
        return contents;
    }

    public void setExponent(BigInteger exponent) {
        this.exponent = exponent;
    }

    public Expr() {
        terms = new ArrayList<>();
    }

    public void addTerm(Term term) {
        terms.add(term);
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
        for (Term term : terms) {
            term.simplify(functionPattern);
            contents.add(term.getContents());
        }
        contents.pow(exponent);
        contents.mergeAll();
        simplified = true;
    }

    public String toString() {
        Iterator<Term> iter = terms.iterator();
        StringBuilder sb = new StringBuilder();
        boolean flag;
        flag = (exponent.compareTo(BigInteger.ONE) > 0);
        boolean needBracket = terms.size() > 1;
        if (needBracket) {
            sb.append("(");
        }
        Term tempTerm = iter.next();
        if (tempTerm.isNegative()) {
            sb.append("-");
        }
        sb.append(tempTerm);
        if (iter.hasNext()) {
            do {
                tempTerm = iter.next();
                if (tempTerm.isNegative()) {
                    sb.append("-");
                }
                else {
                    sb.append("+");
                }
                sb.append(tempTerm);
            } while (iter.hasNext());
        }
        if (needBracket) {
            sb.append(")");
        }
        if (flag) {
            sb.append("^");
            sb.append(exponent);
        }
        return sb.toString();
    }

    public void replacePow(String functionName,FunctionPattern functionPattern,
        ArrayList<Factor> arguments) {
        simplified = false;
        for (Term term : terms) {
            term.replacePow(functionName,functionPattern,arguments);
        }
    }
}
