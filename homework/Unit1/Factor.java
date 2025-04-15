public interface Factor {
    void simplify(FunctionPattern functionPattern);

    Poly getContents();

    Factor getCopy();
}