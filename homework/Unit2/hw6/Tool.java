public class Tool {
    public static int floorToNumber(String str) {
        // 0 -> B1 ; 1 -> F1
        if (str.charAt(0) == 'F') {
            return Integer.parseInt(str.substring(1));
        }
        else {
            return 1 - Integer.parseInt(str.substring(1));
        }
    }

    public static String numberToFloor(int number) {
        StringBuilder stringBuilder = new StringBuilder();
        if (number > 0) {
            stringBuilder.append("F");
            stringBuilder.append(number);
        }
        else {
            stringBuilder.append("B");
            stringBuilder.append(1 - number);
        }
        return stringBuilder.toString();
    }

    public static Status getDir(MyRequest personRequest) {
        // if the passenger need to go up, return true
        if (floorToNumber(personRequest.getToFloor())
            > floorToNumber(personRequest.getFromFloor())) {
            return Status.UP;
        }
        else {
            return Status.DOWN;
        }
    }

    public static boolean reachTop(int currentFloor,Status direction) {
        if (currentFloor == 7 && direction == Status.UP) {
            return true;
        }
        if (currentFloor == -3 && direction == Status.DOWN) {
            return true;
        }
        return false;
    }

    public static Status reverse(Status direction) {
        if (direction == Status.UP) {
            return Status.DOWN;
        }
        else {
            return Status.UP;
        }
    }
}
