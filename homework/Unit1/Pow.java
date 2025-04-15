import java.math.BigInteger;

public class Pow implements Factor {
    private final BigInteger exponent;
    private Poly contents = new Poly();
    private final String varName;
    private boolean simplified = false;

    public String getVarName() {
        return varName;
    }

    public BigInteger getExponent() {
        return exponent;
    }

    public Pow getCopy() {
        Pow pow = new Pow(varName, exponent);
        pow.contents = contents.getCopy();
        return pow;
    }

    public Pow(String varName,BigInteger exponent) {
        this.varName = varName;
        this.exponent = exponent;
    }

    public Poly getContents() {
        return contents;
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
        Mono mono = new Mono(exponent, BigInteger.ONE);
        contents.addMono(mono);
        contents.mergeAll();
        simplified = true;
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        if (exponent.equals(BigInteger.ZERO)) {
            return "1";
        }
        sb.append(varName);
        if (exponent.compareTo(BigInteger.ONE) > 0) {
            sb.append("^");
            sb.append(exponent);
        }
        return sb.toString();
    }
}
