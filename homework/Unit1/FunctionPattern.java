import java.math.BigInteger;
import java.util.ArrayList;

public class FunctionPattern {
    //pattern of the arguments of fn
    //f{n}(x,y) = k1*f{n-1}(f1a1,f1a2) + k2*f{n-2}(f2a1,f2a2) + fnContent
    //inverse = false : (x,y)
    //inverse = true  : (y,x)
    private boolean debugMode = false;
    private Number k1 = new Number(BigInteger.ONE);
    private Number k2 = new Number(BigInteger.ONE);
    private Expr f1a1;
    private Expr f1a2;
    private Expr f2a1;
    private Expr f2a2;
    private ArrayList<Expr> fcontent = new ArrayList<>();
    private Expr fnContent = null;
    private String function1;
    private String function0;
    private String functionn;
    private String functiong;
    private String functionh;
    private Lexer lexer;
    private ArrayList<String> fvarNames = new ArrayList<>();
    private ArrayList<String> gvarNames = new ArrayList<>();
    private ArrayList<String> hvarNames = new ArrayList<>();
    private Expr gcontent;
    private Expr hcontent;
    private int depth;

    public ArrayList<String> getVarNames(String type) {
        if (type.equals("f")) {
            return fvarNames;
        }
        else if (type.equals("g")) {
            return gvarNames;
        }
        else {
            return hvarNames;
        }
    }

    public void setFunction1(String function1) {
        this.function1 = function1;
    }

    public void setFunction0(String function0) {
        this.function0 = function0;
    }

    public void setFunctionn(String functionn) {
        this.functionn = functionn;
    }

    public void setFunctiong(String functiong) {
        this.functiong = functiong;
    }

    public void setFunctionh(String functionh) {
        this.functionh = functionh;
    }

    public void setDepth(int depth) {
        this.depth = depth;
    }

    public void processFunction() {
        if (functiong != null) {
            gcontent = processRegularFunction("g",functiong);
        }
        if (functionh != null) {
            hcontent = processRegularFunction("h",functionh);
        }
        if (function0 != null) {
            fcontent.add(processRegularFunction("f",function0));
            fcontent.add(processRegularFunction("f",function1));
            processFn();
            for (int i = 2; i <= depth; ++i) {
                Pow p0 = new Pow(fvarNames.get(0), BigInteger.ONE);
                Pow p1 = null;
                if (fvarNames.size() > 1) {
                    p1 = new Pow(fvarNames.get(1), BigInteger.ONE);
                }
                ArrayList<Factor> pows = new ArrayList<>();
                pows.add(p0);
                pows.add(p1);
                fcontent.add(functionToExpr("f",i,pows));
            }
        }
        if (debugMode && fcontent.size() != 0) {
            for (int i = 0;i <= 5;++i) {
                System.out.println("f{" + i + "}:"  + fcontent.get(i));
            }
            System.out.println(fnContent);
        }
    }

    private void processFn() {
        lexer = new Lexer(functionn);
        lexer.next(2);// jump into the ',' or ')'
        if (lexer.peek().equals(",")) {
            lexer.next(2);
        } //jump into ')'
        lexer.next(2);
        //jump into the next of '='
        Parser p = new Parser(lexer,this);
        char c = lexer.peek().charAt(0);
        if (c == '+' || c == '-' || Character.isDigit(c)) {
            k1 = p.parseNumber();
            lexer.next(2);//jump into the first argument
        }
        else {
            lexer.next();//jump into the first argument
        }
        f1a1 = p.parseExpr();
        if (lexer.peek().equals(",")) {
            lexer.next();
            f1a2 = p.parseExpr();
        } //jump into the ')'
        //lexer.next();
        c = lexer.peek().charAt(0);
        if (c == '+' || c == '-' || Character.isDigit(c)) {
            k2 = p.parseNumber();
            lexer.next(2);
        }
        else {
            lexer.next();
        }
        f2a1 = p.parseExpr();
        if (lexer.peek().equals(",")) {
            lexer.next();
            f2a2 = p.parseExpr();
        } //jump into the ')'
        if (lexer.peek().equals("+") || lexer.peek().equals("-")) {
            fnContent = p.parseExpr();
        }
    }

    private Expr processRegularFunction(String functionName,String s) {
        ArrayList<String> varNames;
        if (functionName.charAt(0) == 'f') {
            varNames = fvarNames;
        }
        else if (functionName.charAt(0) == 'g') {
            varNames = gvarNames;
        }
        else {
            varNames = hvarNames;
        }
        lexer = new Lexer(s);
        final Parser parser = new Parser(lexer,this);
        lexer.next();
        if (functionName.charAt(0) == 'f') {
            lexer.next(2);
        }
        // jump to ',' or ')'
        varNames.add(lexer.peek());
        lexer.next();
        while (lexer.peek().charAt(0) == ',') {
            lexer.next();
            varNames.add(lexer.peek());
            lexer.next();
        }
        lexer.next(2);
        return parser.parseExpr();
    }

    public Expr functionToExpr(String functionName,int functionNumber,ArrayList<Factor> arguments) {
        if (debugMode) {
            System.out.println("functionNumber: " + functionNumber);
            System.out.println("arguments: " + arguments);
        }
        Expr expr;
        if (functionNumber == 1 || functionNumber == 0) {
            if (functionName.equals("g")) {
                expr = gcontent.getCopy();
            }
            else if (functionName.equals("h")) {
                expr = hcontent.getCopy();
            }
            else {
                if (functionNumber == 0) {
                    expr = fcontent.get(0).getCopy();
                } else {
                    expr = fcontent.get(1).getCopy();
                }
            }
            expr.replacePow(functionName,this, arguments);
            expr.simplify(this);
        }
        else {
            return functionNToExpr(functionNumber,arguments);
        }
        if (debugMode) {
            System.out.println("expr: " + expr);
        }
        return expr;
    }

    public Expr functionNToExpr(int functionNumber,ArrayList<Factor> arguments) {
        Expr expr;
        if (fcontent.size() >= functionNumber + 1) {
            expr = fcontent.get(functionNumber).getCopy();
            expr.replacePow("f",this, arguments);
            if (debugMode) {
                System.out.println("expr: " + expr);
            }
            return expr;
        }
        expr = new Expr();
        if (!k1.getVal().equals(BigInteger.ZERO)) {
            Term term1 = new Term();
            term1.addFactor(k1);
            Function function = new Function("f",functionNumber - 1);
            Expr temp = f1a1.getCopy();
            //temp.replacePow("f",this,arguments);
            function.addArgument(temp);
            if (f1a2 != null) {
                temp = f1a2.getCopy();
                //temp.replacePow("f",this,arguments);
                function.addArgument(temp);
            }
            term1.addFactor(function);
            expr.addTerm(term1);
        }
        if (!k2.getVal().equals(BigInteger.ZERO)) {
            Term term2 = new Term();
            term2.addFactor(k2);
            Function function = new Function("f",functionNumber - 2);
            Expr temp = f2a1.getCopy();
            //temp.replacePow("f",this,arguments);
            function.addArgument(temp);
            if (f2a2 != null) {
                temp = f2a2.getCopy();
                //temp.replacePow("f",this,arguments);
                function.addArgument(temp);
            }
            term2.addFactor(function);
            expr.addTerm(term2);
        }
        Term term = new Term();
        if (fnContent != null) {
            Expr tempFactor = fnContent.getCopy();
            //tempFactor.replacePow("f",this,arguments);
            term.addFactor(tempFactor);
            expr.addTerm(term);
        }
        expr.simplify(this);
        return expr;
    }
}

