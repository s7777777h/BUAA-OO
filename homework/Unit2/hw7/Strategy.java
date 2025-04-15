//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

public class Strategy {
    private final WaitingList waitingList;
    private final Elevator elevator;
    private final WaitingList inside;

    public Strategy(WaitingList waitingList, WaitingList inside, Elevator elevator) {
        this.waitingList = waitingList;
        this.inside = inside;
        this.elevator = elevator;
    }

    public Advice getAdvice(int curFloor, Status status, Status direction) {
        if (this.waitingList.haveSchedule()) {
            return Advice.SCHE;
        }
        else if (this.waitingList.haveUpdateList()) {
            return Advice.UPDATE;
        }
        else if (this.waitingList.isEmpty() && this.inside.isEmpty()) {
            if (elevator.inSharedFloor()) {
                if (elevator.getKind() == 1) {
                    if (direction == Status.DOWN) {
                        return Advice.REVERSE;
                    }
                    return Advice.MOVE;
                }
                else if (elevator.getKind() == -1) {
                    if (direction == Status.UP) {
                        return Advice.REVERSE;
                    }
                    return Advice.MOVE;
                }
            }
            return Advice.WAIT;
        } else if (elevator.needOut(curFloor)) {
            return Advice.OPEN;
        } else if (this.waitingList.needIn(curFloor, direction) && this.inside.size() < 6) {
            return Advice.OPEN;
        } else if (elevator.reachTop()) {
            if (this.waitingList.needIn(curFloor, Tool.reverse(direction))) {
                return Advice.OPEN;
            } else {
                if (Debug.d()) {
                    System.out.println("[LOG]reverse reason: reach top");
                }
                return Advice.REVERSE;
            }
        } else if (!this.inside.isEmpty()) {
            if (inside.haveDir(direction)) {
                return Advice.MOVE;
            } else {
                return Advice.REVERSE;
            }
        } else if (direction == Status.UP) {
            if (this.waitingList.checkPresentRequestUp(curFloor)) {
                return Advice.MOVE;
            } else {
                if (Debug.d()) {
                    System.out.println("[LOG]move reason:moving up but no request up");
                }
                return Advice.REVERSE;
            }
        } else if (this.waitingList.checkPresentRequestDown(curFloor)) {
            return Advice.MOVE;
        } else {
            if (Debug.d()) {
                System.out.println("[LOG]move reason:moving down but no request down");
            }
            return Advice.REVERSE;
        }
    }
}
