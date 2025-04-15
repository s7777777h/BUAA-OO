public class Lexer {
    private final String input;
    private int pos = 0;
    private String curToken;

    public Lexer(String input) {
        this.input = input;
        this.next();
    }

    private String getNumber() {
        StringBuilder sb = new StringBuilder();
        while (pos < input.length() && Character.isDigit(input.charAt(pos))) {
            sb.append(input.charAt(pos));
            ++pos;
        }
        return sb.toString();
    }

    public void next(Integer x) {
        for (int i = 0; i < x; ++i) {
            next();
        }
    }

    public void next() {
        if (pos == input.length()) {
            return;
        }
        char c = input.charAt(pos);
        if (Character.isDigit(c)) {
            curToken = getNumber();
        }
        else if (c == '+' || c == '*' || c == '(' || c == ')' || c == '-' || c == '^') {
            pos += 1;
            curToken = String.valueOf(c);
        }
        else if (c == 'x' || c == 'y' || c == ',' || c == '=') {
            pos += 1;
            curToken = String.valueOf(c);
        }
        else if (c == 'f' || c == 'g' || c == 'h' || c == '}') {
            pos += 2;
            curToken = String.valueOf(c);
            if (c == 'f' && input.charAt(pos) == 'n') {
                if (input.charAt(pos + 1) == '-') {
                    pos += 5;
                }
                else {
                    pos += 3;
                }
            }
            //if f{n} jump into the first argument
            //else jump into the number of the function
        }
        else if (c == 'd') {
            pos += 3;
            curToken = String.valueOf(c);
        }
        else if (c == 'c' || c == 's') {
            pos += 4;
            curToken = String.valueOf(c);
        }
        //if cos or sin,jump into the argument
    }

    public String peek() {
        return curToken;
    }
}
