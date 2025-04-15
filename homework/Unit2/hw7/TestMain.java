//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Objects;
import java.util.Queue;
import java.util.Scanner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.IntStream;

public class TestMain {
    public TestMain() {
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        ArrayList<String> lines = new ArrayList();

        while(scanner.hasNextLine()) {
            lines.add(scanner.nextLine());
        }

        System.setIn(new TimeInputStream(lines));

        try {
            Main.main(args);
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private static class Pair<K, V> {
        private final K first;
        private final V second;

        Pair(K first, V second) {
            this.first = first;
            this.second = second;
        }

        public K getFirst() {
            return this.first;
        }

        public V getSecond() {
            return this.second;
        }

        public boolean equals(Object obj) {
            if (this == obj) {
                return true;
            } else if (obj != null && this.getClass() == obj.getClass()) {
                Pair<?, ?> pair = (Pair)obj;
                return Objects.equals(this.first, pair.first) && Objects.equals(this.second, pair.second);
            } else {
                return false;
            }
        }

        public int hashCode() {
            return Objects.hash(new Object[]{this.first, this.second});
        }

        public String toString() {
            return "<" + this.first + ", " + this.second + ">";
        }
    }

    private static class TimeInputStream extends InputStream {
        private static final Pattern pattern = Pattern.compile("\\[(.*?)](.*)");
        private final Queue<Pair<Long, String>> data = new ArrayDeque();
        private final Queue<Integer> cache = new ArrayDeque();

        TimeInputStream(ArrayList<String> lines) {
            long initTime = System.currentTimeMillis();

            for(String line : lines) {
                Matcher matcher = pattern.matcher(line);
                if (!matcher.find()) {
                    throw new RuntimeException("Invalid input: " + line);
                }

                long time = (long)(Double.parseDouble(matcher.group(1)) * (double)1000.0F + (double)0.5F);
                String content = matcher.group(2);
                this.data.add(new Pair(initTime + time, content));
            }

        }

        public int read() throws IOException {
            if (this.cache.isEmpty()) {
                if (this.data.isEmpty()) {
                    return -1;
                }

                try {
                    long time = (Long)((Pair)this.data.peek()).getFirst() - System.currentTimeMillis();
                    if (time > 0L) {
                        Thread.sleep(time);
                    }

                    String content = (String)((Pair)Objects.requireNonNull(this.data.poll())).getSecond();
                    IntStream var10000 = content.chars();
                    Queue var10001 = this.cache;
                    var10000.forEach(var10001::add);
                    this.cache.add(10);
                } catch (InterruptedException e) {
                    throw new IOException(e);
                }
            }

            return (Integer)Objects.requireNonNull(this.cache.poll());
        }

        public int read(byte[] b, int off, int len) throws IOException {
            if (b == null) {
                throw new NullPointerException();
            } else if (off >= 0 && len >= 0 && len <= b.length - off) {
                if (len == 0) {
                    return 0;
                } else {
                    int c = this.read();
                    if (c == -1) {
                        return -1;
                    } else {
                        b[off] = (byte)c;

                        int i;
                        for(i = 1; i < len && !this.cache.isEmpty(); ++i) {
                            c = this.read();
                            if (c == -1) {
                                break;
                            }

                            b[off + i] = (byte)c;
                        }

                        return i;
                    }
                }
            } else {
                throw new IndexOutOfBoundsException();
            }
        }
    }
}
