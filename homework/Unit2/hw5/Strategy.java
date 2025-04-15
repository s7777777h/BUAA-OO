public class Strategy {
    private WaitingList waitingList;
    private Elevator elevator;
    private WaitingList inside;

    public Strategy(WaitingList waitingList,WaitingList inside, Elevator elevator) {
        this.waitingList = waitingList;
        this.inside = inside;
        this.elevator = elevator;
    }

    public Advice getAdvice(int curFloor, Status status, Status direction) {
        if (waitingList.isEmpty() && inside.isEmpty()) {
            return Advice.WAIT;
        }
        if (inside.needOut(curFloor)) {
            return Advice.OPEN;
        }
        if (waitingList.needIn(curFloor, direction) && inside.size() < 6) {
            return Advice.OPEN;
        }
        if (Tool.reachTop(curFloor,direction)) {
            if (waitingList.needIn(curFloor, Tool.reverse(direction))) {
                return Advice.OPEN;
            }
            return Advice.REVERSE;
        }
        if (!inside.isEmpty()) {
            if (direction == Tool.getDir(inside.get(0))) {
                return Advice.MOVE;
            }
            return Advice.REVERSE;
        }
        if (direction == Status.UP) {
            if (waitingList.checkPresentRequestUp(curFloor)) {
                return Advice.MOVE;
            }
            return Advice.REVERSE;
        }
        else {
            if (waitingList.checkPresentRequestDown(curFloor)) {
                return Advice.MOVE;
            }
            return Advice.REVERSE;
        }
    }
}
