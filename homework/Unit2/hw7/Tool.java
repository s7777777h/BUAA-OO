//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

import static java.lang.Thread.sleep;

public class Tool {
    public Tool() {
    }

    public static int floorToNumber(String str) {
        return str.charAt(0) == 'F' ? Integer.parseInt(str.substring(1)) :
            1 - Integer.parseInt(str.substring(1));
    }

    public static void goodSleep(long time) {
        try {
            sleep(time);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    public static String numberToFloor(int number) {
        StringBuilder stringBuilder = new StringBuilder();
        if (number > 0) {
            stringBuilder.append("F");
            stringBuilder.append(number);
        } else {
            stringBuilder.append("B");
            stringBuilder.append(1 - number);
        }

        return stringBuilder.toString();
    }

    public static Status getDir(MyRequest personRequest) {
        return floorToNumber(personRequest.getToFloor()) >
            floorToNumber(personRequest.getPresentFloor()) ? Status.UP : Status.DOWN;
    }

    public static Status getDir(int fromFloor, int toFloor) {
        return fromFloor > toFloor ? Status.DOWN : Status.UP;
    }

    public static Status reverse(Status direction) {
        return direction == Status.UP ? Status.DOWN : Status.UP;
    }
}
