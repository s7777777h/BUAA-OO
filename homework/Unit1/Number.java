import java.math.BigInteger;

public class Number implements Factor {
    private final BigInteger val;
    private final String num;
    private Poly contents = new Poly();

    public BigInteger getVal() {
        return val;
    }

    public Number getCopy() {
        Number number = new Number(val);
        number.contents = contents.getCopy();
        return number;
    }

    public Number(BigInteger val) {
        this.val = val;
        num = val.toString();
    }

    public Poly getContents() {
        return contents;
    }

    public void simplify(FunctionPattern functionPattern) {
        contents = new Poly();
        Mono mono = new Mono(BigInteger.ZERO, val);
        contents.addMono(mono);
    }

    public String toString() {
        return num;
    }
}
