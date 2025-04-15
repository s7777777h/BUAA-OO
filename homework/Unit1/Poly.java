import java.math.BigInteger;
import java.util.ArrayList;

public class Poly {
    private ArrayList<Mono> content = new ArrayList<>();

    public int getSize() {
        return content.size();
    }

    public void clear() {
        content.clear();
    }

    public boolean equalsToZero() {
        if (content.isEmpty()) {
            return true;
        }
        else if (content.size() == 1) {
            if (content.get(0).getCoefficient().equals(BigInteger.ZERO)) {
                return true;
            }
        }
        return false;
    }

    public Poly getCopy() {
        Poly poly = new Poly();
        poly.content.addAll(content);
        return poly;
    }

    public Poly getDerivation() {
        Poly poly = new Poly();
        for (Mono mono : content) {
            poly.add(mono.getDerivation());
        }
        return poly;
    }

    public boolean equals(Poly p) {
        if (this.content.size() != p.content.size()) {
            return false;
        }
        for (Mono mono1 : this.content) {
            boolean flag = false;
            for (Mono mono2 : p.content) {
                if (mono1.equals(mono2)) {
                    flag = true;
                }
            }
            if (!flag) {
                return false;
            }
        }
        return true;
    }

    public void add(Poly p) {
        for (Mono mono1 : p.content) {
            boolean flag = false;
            for (Mono mono : this.content) {
                if (mono.mergeAble(mono1)) {
                    flag = true;
                    mono.add(mono1);
                    break;
                }
            }
            if (!flag) {
                content.add(mono1);
            }
        }
    }

    public void mul(Poly p) {
        ArrayList<Mono> newContent = new ArrayList<>();
        for (Mono mono1 : p.content) {
            for (Mono mono : this.content) {
                newContent.add(mono.mul(mono1));
            }
        }
        mergeAll();
        this.content = newContent;
    }

    public void simplify() {
        for (int i = 0; i < content.size(); i++) {
            Factor factor1 = content.get(i).potential();
            if (factor1 == null) {
                continue;
            }
            for (int j = i + 1; j < content.size();) {
                Factor factor2 = content.get(j).potential();
                if (factor2 == null) {
                    ++j;
                    continue;
                }
                if (factor1.getContents().equals(factor2.getContents())) {
                    BigInteger subValue = content.get(j).getCoefficient();
                    content.get(i).subCoefficient(subValue);
                    content.remove(j);
                    boolean tempFlag = false;
                    for (Mono mono : content) {
                        if (mono.isNumber()) {
                            mono.addCoefficient(subValue);
                            tempFlag = true;
                        }
                    }
                    if (!tempFlag) {
                        Mono newMono = new Mono(BigInteger.ZERO, subValue);
                        content.add(newMono);
                    }
                    if (content.get(i).getCoefficient().equals(BigInteger.ZERO)) {
                        content.remove(i);
                        --i;
                        --j;
                    }
                }
                else {
                    ++j;
                }
            }
        }
    }

    public void mergeAll() {
        boolean changed;
        do {
            changed = false;
            for (int i = 0; i < content.size(); i++) {
                Mono current = content.get(i);
                for (int j = i + 1; j < content.size();) {
                    Mono other = content.get(j);
                    if (current.mergeAble(other)) {
                        current.add(other);
                        content.remove(j);
                        changed = true;
                    } else {
                        j++;
                    }
                }
            }
        } while (changed);
        simplify();
    }

    public void pow(BigInteger exponent) {
        Poly p = getCopy();
        for (int i = 1; i < exponent.intValue(); i++) {
            mul(p);
        }
    }

    public void addMono(Mono mono) {
        for (Mono mono1 : this.content) {
            if (mono1.mergeAble(mono)) {
                mono1.add(mono);
                return;
            }
        }
        content.add(mono);
    }

    public void print() {
        boolean flag = false;
        int firstPos = -1;
        for (int i = 0; i < this.content.size(); i++) {
            if (content.get(i).isPositive()) {
                content.get(i).print(true);
                firstPos = i;
                flag = true;
                break;
            }

        }
        for (int i = 0; i < this.content.size(); i++) {
            Mono mono = this.content.get(i);
            if (i == firstPos) {
                continue;
            }
            flag |= mono.print(false);
        }
        if (!flag) {
            System.out.print("0");
        }
    }

    public boolean needDoubleBrackets() {
        if (this.content.size() != 1) {
            return true;
        }
        Mono mono = this.content.get(0);
        return mono.needDoubleBrackets();
    }
}
