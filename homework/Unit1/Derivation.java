import java.util.ArrayList;

public class Derivation implements Factor, Branch {
    private Expr expr;
    private Poly contents = new Poly();

    public Derivation(Expr expr) {
        this.expr = expr;
    }

    public Poly getContents() {
        return contents;
    }

    public Derivation getCopy() {
        Derivation copy = new Derivation(expr);
        copy.contents = contents.getCopy();
        return copy;
    }

    public void simplify(FunctionPattern functionPattern) {
        expr.simplify(functionPattern);
        contents = expr.getContents().getDerivation();
    }

    public void replacePow(String functionName, FunctionPattern functionPattern,
        ArrayList<Factor> arguments) {
        expr.replacePow(functionName, functionPattern, arguments);
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("dx(");
        sb.append(expr);
        sb.append(")");
        return sb.toString();
    }
}
