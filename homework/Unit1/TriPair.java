import java.math.BigInteger;

public class TriPair {
    private BigInteger exponent;
    private Factor content;

    public TriPair(BigInteger exponent, Factor content) {
        this.exponent = exponent;
        this.content = content;
    }

    public BigInteger getExponent() {
        return exponent;
    }

    public Factor getContent() {
        return content;
    }

    public TriPair getCopy() {
        return new TriPair(exponent, content);
    }
}
