import java.math.BigInteger;

public class Parser {
    private final Lexer lexer;
    private final FunctionPattern functionPattern;

    public Parser(Lexer lexer,FunctionPattern functionPattern) {
        this.lexer = lexer;
        this.functionPattern = new FunctionPattern();
    }

    public Derivation parseDerivation() {
        lexer.next();
        Derivation derivation = new Derivation(parseExpr());
        return derivation;
    }

    public Number parseNumber() {
        BigInteger val;
        if (Character.isDigit(lexer.peek().charAt(0))) {
            val = new BigInteger(lexer.peek());
        }
        else {
            char c = lexer.peek().charAt(0);
            lexer.next();
            val = new BigInteger(lexer.peek());
            if (c == '-') {
                val = val.negate();
            }
        }
        lexer.next();
        return new Number(val);
    }

    public Expr parseExpr() {
        final Expr expr = new Expr();
        boolean flag = (lexer.peek().charAt(0) == '-');
        if (flag) {
            lexer.next();
        }
        while (lexer.peek().equals("+")) {
            lexer.next();
        }
        Term tempTerm = parseTerm();
        if (flag) {
            tempTerm.negate();
        }
        expr.addTerm(tempTerm);
        while (lexer.peek().charAt(0) == '+' || lexer.peek().charAt(0) == '-') {
            boolean flag2 = (lexer.peek().charAt(0) == '-');
            lexer.next();
            Term tempTerm2 = parseTerm();
            if (flag2) {
                tempTerm2.negate();
            }
            expr.addTerm(tempTerm2);
        }
        if (lexer.peek().charAt(0) == ')') {
            lexer.next();
            if (lexer.peek().charAt(0) == '^') {
                lexer.next();
                if (lexer.peek().charAt(0) == '+') {
                    lexer.next();
                }
                expr.setExponent(new BigInteger(lexer.peek()));
                lexer.next();
            }
        }
        return expr;
    }

    private Term parseTerm() {
        Term term = new Term();
        term.addFactor(parseFactor());
        while (lexer.peek().charAt(0) == '*') {
            lexer.next();
            term.addFactor(parseFactor());
        }
        return term;
    }

    private Function parseFunction(String functionName) {
        boolean flag = (lexer.peek().charAt(0) == 'f');
        lexer.next();
        Integer functionNum = 0;
        if (flag) {
            functionNum = Integer.parseInt(lexer.peek());
            lexer.next(2);
        }
        Function function = new Function(functionName,functionNum);
        function.addArgument(parseFactor());
        while (lexer.peek().charAt(0) == ',') {
            lexer.next();
            function.addArgument(parseFactor());
        }
        lexer.next();
        return function;
    }

    private Factor parseTriFunc() {
        boolean isSine;
        isSine = (lexer.peek().charAt(0) == 's');
        lexer.next();
        final Factor tempFactor = parseFactor();
        BigInteger exponent = BigInteger.ONE;
        lexer.next();
        if (lexer.peek().charAt(0) == '^') {
            lexer.next();
            if (lexer.peek().charAt(0) == '+') {
                lexer.next();
            }
            exponent = new BigInteger(lexer.peek());
            lexer.next();
        }
        if (exponent.equals(BigInteger.ZERO)) {
            return new Number(BigInteger.ONE);
        }
        return new TriFunc(isSine, tempFactor, exponent);
    }

    public Factor parseFactor() {
        while (lexer.peek().charAt(0) == '+') {
            lexer.next();
        }
        if (lexer.peek().equals("(")) {
            lexer.next();
            return parseExpr();
        }
        else if (lexer.peek().equals("x") || lexer.peek().equals("y")) {
            String varName = lexer.peek();
            lexer.next();
            if (lexer.peek().equals("^")) {
                lexer.next();
                if (lexer.peek().charAt(0) == '+') {
                    lexer.next();
                }
                BigInteger temp = new BigInteger(lexer.peek());
                lexer.next();
                return new Pow(varName, temp);
            }
            return new Pow(varName,BigInteger.ONE);
        }
        else if (lexer.peek().equals("s") || lexer.peek().equals("c")) {
            return parseTriFunc();
        }
        else if (lexer.peek().equals("f") || lexer.peek().equals("g") || lexer.peek().equals("h")) {
            return parseFunction(lexer.peek());
        }
        else if (lexer.peek().equals("d")) {
            return parseDerivation();
        }
        else {
            return parseNumber();
        }
    }
}
