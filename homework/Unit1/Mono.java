import java.math.BigInteger;
import java.util.ArrayList;

public class Mono {
    private BigInteger exponent;
    private BigInteger coefficient;
    private final ArrayList<TriPair> sin = new ArrayList<>();
    private final ArrayList<TriPair> cos = new ArrayList<>();

    private ArrayList<TriPair> getSinCopy() {
        ArrayList<TriPair> copy = new ArrayList<>();
        copy.addAll(sin);
        return copy;
    }

    private ArrayList<TriPair> getCosCopy() {
        ArrayList<TriPair> copy = new ArrayList<>();
        copy.addAll(cos);
        return copy;
    }

    public boolean isPositive() {
        return coefficient.compareTo(BigInteger.ZERO) > 0;
    }

    public Poly getDerivation() {
        Poly poly = new Poly();
        if ((exponent.equals(BigInteger.ZERO) && sin.isEmpty() && cos.isEmpty())
            || coefficient.equals(BigInteger.ZERO)) {
            Mono temp = new Mono(BigInteger.ZERO, BigInteger.ZERO);
            poly.addMono(temp);
            return poly;
        }
        else if (sin.isEmpty() && cos.isEmpty()) {
            Mono temp = new Mono(exponent.subtract(BigInteger.ONE),exponent.multiply(coefficient));
            poly.addMono(temp);
            return poly;
        }
        else if (exponent.equals(BigInteger.ZERO) && sin.isEmpty() && cos.size() == 1) {
            BigInteger cosExp = cos.get(0).getExponent();
            Factor cosPoly = cos.get(0).getContent();
            Mono temp = new Mono(BigInteger.ZERO, coefficient.multiply(cosExp).negate());
            if (cosExp.compareTo(BigInteger.ONE) > 0) {
                temp.addCos(cosPoly,cosExp.subtract(BigInteger.ONE));
            }
            temp.addSin(cosPoly,BigInteger.ONE);
            poly.addMono(temp);
            poly.mul(cosPoly.getContents().getDerivation());
            return poly;
        }
        else if (exponent.equals(BigInteger.ZERO) && cos.isEmpty() && sin.size() == 1) {
            BigInteger sinExp = sin.get(0).getExponent();
            Factor sinPoly = sin.get(0).getContent();
            Mono temp = new Mono(BigInteger.ZERO, coefficient.multiply(sinExp));
            if (sinExp.compareTo(BigInteger.ONE) > 0) {
                temp.addSin(sinPoly,sinExp.subtract(BigInteger.ONE));
            }
            temp.addCos(sinPoly,BigInteger.ONE);
            poly.addMono(temp);
            poly.mul(sinPoly.getContents().getDerivation());
            return poly;
        }
        else {
            poly = getRegularDerivation();
        }
        return poly;
    }

    private Poly getRegularDerivation() {
        if (!exponent.equals(BigInteger.ZERO)) {    //knx^{n-1}[sin...cos...] + kx^n[sin...cos...]'
            Poly poly1 = new Poly();
            Mono mono1 = new Mono(exponent.subtract(BigInteger.ONE),exponent.multiply(coefficient));
            mono1.sin.addAll(sin);
            mono1.cos.addAll(cos);
            poly1.addMono(mono1);   //up: first term
            Poly poly2 = new Poly();
            Mono mono2 = new Mono(exponent,coefficient);
            poly2.addMono(mono2);
            Mono mono3 = new Mono(BigInteger.ZERO,BigInteger.ONE);
            mono3.sin.addAll(sin);
            mono3.cos.addAll(cos);
            poly2.mul(mono3.getDerivation());   //up: second term
            poly1.add(poly2);
            return poly1;
        }
        else if (exponent.equals(BigInteger.ZERO) && !cos.isEmpty()) {
            Mono mono1 = new Mono(BigInteger.ZERO,coefficient); //mono 1 :last cos function
            TriPair last = cos.get(cos.size() - 1);
            Poly poly1 = new Poly();
            mono1.addCos(last.getContent(),last.getExponent());
            poly1.addMono(mono1.getCopy());
            Mono mono2 = new Mono(BigInteger.ZERO,BigInteger.ONE); //mono 2 : other
            mono2.cos.addAll(cos);
            mono2.sin.addAll(sin);
            mono2.cos.remove(last);
            poly1.mul(mono2.getDerivation());
            Poly poly2 = new Poly();
            poly2.addMono(mono2);
            poly2.mul(mono1.getDerivation());
            poly1.add(poly2);
            return poly1;
        }
        else {
            Mono mono1 = new Mono(BigInteger.ZERO,coefficient); //mono 1 :last cos function
            TriPair last = sin.get(sin.size() - 1);
            Poly poly1 = new Poly();
            mono1.addSin(last.getContent(),last.getExponent());
            poly1.addMono(mono1.getCopy());
            Mono mono2 = new Mono(BigInteger.ZERO,BigInteger.ONE); //mono 2 : other
            mono2.cos.addAll(cos);
            mono2.sin.addAll(sin);
            mono2.sin.remove(last);
            poly1.mul(mono2.getDerivation());
            Poly poly2 = new Poly();
            poly2.addMono(mono2);
            poly2.mul(mono1.getDerivation());
            poly1.add(poly2);
            return poly1;
        }
    }

    public Mono getCopy() {
        Mono mono = new Mono(exponent, coefficient);
        for (TriPair triPair : sin) {
            mono.sin.add(triPair.getCopy());
        }
        for (TriPair triPair : cos) {
            mono.cos.add(triPair.getCopy());
        }
        return mono;
    }

    public boolean mergeAble(Mono mono) {
        if (!exponent.equals(mono.exponent)) {
            return false;
        }
        if (sin.isEmpty() && cos.isEmpty() && mono.sin.isEmpty() && mono.cos.isEmpty()) {
            return true;
        }
        if (sin.size() != mono.sin.size() || cos.size() != mono.cos.size()) {
            return false;
        }
        if (!checkHashMap(sin,mono.sin) || !checkHashMap(mono.sin,sin)) {
            return false;
        }
        if (!checkHashMap(cos,mono.cos) || !checkHashMap(cos,mono.cos)) {
            return false;
        }
        return true;
    }

    public boolean equals(Mono mono) {
        return (coefficient.equals(mono.coefficient) && mergeAble(mono));
    }

    private boolean checkHashMap(ArrayList<TriPair> m1, ArrayList<TriPair> m2) {
        for (TriPair triPair1 : m1) {
            Factor factor1 = triPair1.getContent();
            boolean flag = false;
            for (TriPair triPair2 : m2) {
                Factor factor2 = triPair2.getContent();
                if (factor1.getContents().equals(factor2.getContents())) {
                    if (!triPair1.getExponent().equals(triPair2.getExponent())) {
                        return false;
                    }
                    flag = true;
                }
            }
            if (!flag) {
                return false;
            }
        }
        return true;
    }

    public Mono(BigInteger exponent, BigInteger coefficient) {
        this.exponent = exponent;
        this.coefficient = coefficient;
    }

    public void addSin(Factor factor,BigInteger exponent) {
        if (exponent.equals(BigInteger.ZERO)) {
            return;
        }
        else if (factor.getContents().equalsToZero()) {
            coefficient = BigInteger.ZERO;
            sin.clear();
            cos.clear();
            this.exponent = BigInteger.ZERO;
        }
        for (int i = 0;i < sin.size();i++) {
            TriPair triPair = sin.get(i);
            Factor factor1 = triPair.getContent();
            if (factor1.getContents().equals(factor.getContents())) {
                sin.set(i,new TriPair(triPair.getExponent().add(exponent), factor));
                return;
            }
        }
        sin.add(new TriPair(exponent, factor));
    }

    public void addCos(Factor factor,BigInteger exponent) {
        if (exponent.equals(BigInteger.ZERO) || factor.getContents().equalsToZero()) {
            return;
        }
        for (int i = 0;i < cos.size();i++) {
            TriPair triPair = cos.get(i);
            Factor factor1 = triPair.getContent();
            if (factor1.getContents().equals(factor.getContents())) {
                cos.set(i,new TriPair(triPair.getExponent().add(exponent), factor));
                return;
            }
        }
        cos.add(new TriPair(exponent, factor));
    }

    public Mono mul(Mono mono) {
        if (coefficient.equals(BigInteger.ZERO) || mono.coefficient.equals(BigInteger.ZERO)) {
            return new Mono(BigInteger.ZERO, BigInteger.ZERO);
        }
        Mono newMono = new Mono(exponent.add(mono.exponent),coefficient.multiply(mono.coefficient));
        newMono.sin.addAll(sin);
        newMono.cos.addAll(cos);
        for (int i = 0; i < mono.sin.size(); i++) {
            TriPair triPair = mono.sin.get(i);
            Factor factor = triPair.getContent();
            boolean flag = false;
            for (int j = 0;j < sin.size();j++) {
                TriPair triPair1 = sin.get(j);
                Factor factor1 = triPair1.getContent();
                if (factor.getContents().equals(factor1.getContents())) {
                    BigInteger newExponent = triPair1.getExponent().add(triPair.getExponent());
                    newMono.sin.set(j,new TriPair(newExponent, factor));
                    flag = true;
                }
            }
            if (!flag) {
                newMono.sin.add(new TriPair(triPair.getExponent(),factor));
            }
        }
        for (int i = 0; i < mono.cos.size(); i++) {
            TriPair triPair = mono.cos.get(i);
            Factor factor = triPair.getContent();
            boolean flag = false;
            for (int j = 0;j < cos.size();j++) {
                TriPair triPair1 = cos.get(j);
                Factor factor1 = triPair1.getContent();
                if (factor.getContents().equals(factor1.getContents())) {
                    BigInteger newExponent = triPair1.getExponent().add(triPair.getExponent());
                    newMono.cos.set(j, new TriPair(newExponent, factor));
                    flag = true;
                }
            }
            if (!flag) {
                newMono.cos.add(new TriPair(triPair.getExponent(),factor));
            }
        }
        return newMono;
    }

    public void add(Mono mono) {
        coefficient = coefficient.add(mono.coefficient);
        if (coefficient.equals(BigInteger.ZERO)) {
            sin.clear();
            cos.clear();
            exponent = BigInteger.ZERO;
        }
    }

    public boolean print(boolean isFirst) {
        if (coefficient.equals(BigInteger.ZERO)) {
            return false;
        }
        if (coefficient.compareTo(BigInteger.ZERO) > 0 && !isFirst) {
            System.out.print("+");
        }
        if (exponent.equals(BigInteger.ZERO) && sin.isEmpty() && cos.isEmpty()) {
            System.out.print(coefficient);
            return true;
        }
        boolean flag = false;
        if (!coefficient.abs().equals(BigInteger.ONE)) {
            System.out.print(coefficient);
            flag = true;
        }
        if (coefficient.negate().equals(BigInteger.ONE)) {
            System.out.print("-");
        }
        if (exponent.compareTo(BigInteger.ZERO) > 0) {
            if (flag) {
                System.out.print("*");
            }
            System.out.print("x");
            if (exponent.compareTo(BigInteger.ONE) > 0) {
                System.out.print("^" + exponent);
            }
            flag = true;
        }
        flag = printSinOrCos(flag,false);
        printSinOrCos(flag,true);
        return true;
    }

    public boolean printSinOrCos(boolean flag1,boolean type) {
        boolean flag = flag1;
        ArrayList<TriPair> sinOrCos;
        if (type) {
            sinOrCos = cos;
        }
        else {
            sinOrCos = sin;
        }
        for (TriPair triPair : sinOrCos) {
            Factor factor = triPair.getContent();
            if (flag) {
                System.out.print("*");
            }
            boolean needDoubleBrackets = factor.getContents().needDoubleBrackets();
            if (!type) {
                System.out.print("sin(");
            }
            else {
                System.out.print("cos(");
            }
            if (needDoubleBrackets) {
                System.out.print("(");
            }
            factor.getContents().print();
            if (needDoubleBrackets) {
                System.out.print(")");
            }
            System.out.print(")");
            if (!triPair.getExponent().equals(BigInteger.ONE)) {
                System.out.print("^" + triPair.getExponent());
            }
            flag = true;
        }
        return flag;
    }

    public boolean needDoubleBrackets() {
        if (sin.isEmpty() && cos.isEmpty()) {
            if (exponent.equals(BigInteger.ZERO)) {
                return false;
            }
            if (coefficient.equals(BigInteger.ONE)) {
                return false;
            }
        }
        if (!(exponent.equals(BigInteger.ZERO) && coefficient.equals(BigInteger.ONE))) {
            return true;
        }
        if (sin.size() >= 2 || cos.size() >= 2) {
            return true;
        }
        if (!sin.isEmpty() && !cos.isEmpty()) {
            return true;
        }
        return false;
    }

    public Factor potential() { //have the potential to be simplified
        if ((sin.isEmpty() && cos.isEmpty()) || (!sin.isEmpty() && !cos.isEmpty())) {
            return null;
        }
        if (!exponent.equals(BigInteger.ZERO)) {
            return null;
        }
        if (sin.size() >= 2 || cos.size() >= 2) {
            return null;
        }
        for (TriPair triPair : sin) {
            if (triPair.getExponent().equals(new BigInteger("2"))) {
                return triPair.getContent();
            }
        }
        for (TriPair triPair : cos) {
            if (triPair.getExponent().equals(new BigInteger("2"))) {
                return triPair.getContent();
            }
        }
        return null;
    }

    public BigInteger getCoefficient() {
        return coefficient;
    }

    public void subCoefficient(BigInteger subValue) {
        coefficient = coefficient.subtract(subValue);
    }

    public void addCoefficient(BigInteger addValue) {
        coefficient = coefficient.add(addValue);
    }

    public boolean isNumber() {
        return (sin.isEmpty() && cos.isEmpty() && exponent.equals(BigInteger.ZERO));
    }
}
