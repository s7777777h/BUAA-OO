import com.oocourse.elevator1.TimableOutput;

import java.util.ArrayList;

public class Elevator extends Thread {
    private int elevatorId;
    private int currentFloor;
    private int size;
    private final int maxSize = 6;
    private boolean isEnd = false;
    private Status status;
    private Status direction;
    private WaitingList waitingList = new WaitingList();
    private WaitingList inside = new WaitingList();
    private Strategy strategy = new Strategy(waitingList,inside,this);

    public Elevator(int elevatorId) {
        this.elevatorId = elevatorId;
        this.status = Status.WAITING;
        this.direction = Status.UP;
        this.currentFloor = 1;
    }

    public void setIsEnd() {
        isEnd = true;
    }

    public void run() {
        while (true) {
            Advice advice;
            synchronized (waitingList) {
                advice = strategy.getAdvice(currentFloor,status,direction);
            }
            if (Debug.d()) {
                System.out.println(advice.toString());
            }
            if (advice == Advice.MOVE || advice == Advice.REVERSE) {
                move(advice);
            }
            if (advice == Advice.OPEN) {
                synchronized (waitingList) {
                    getOut();
                    getIn(direction);
                }
                if (inside.isEmpty()) {
                    synchronized (waitingList) {
                        getIn(Tool.reverse(direction));
                    }
                    direction = Tool.reverse(direction);
                }
                try {
                    sleep(400);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
                getIn(direction);
                TimableOutput.println("CLOSE-" +
                    Tool.numberToFloor(currentFloor) + "-" + elevatorId);
                status = Status.MOVING;
            }
            if (advice == Advice.WAIT) {
                synchronized (waitingList) {
                    if (Debug.d()) {
                        //    System.out.println("Elevator " + elevatorId + " is waiting");
                    }
                    status = Status.WAITING;
                    if (isEnd) {
                        if (Debug.d()) {
                            System.out.println("Elevator " + elevatorId + " is end");
                        }
                        return;
                    }
                    try {
                        waitingList.wait();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
            }
        }
    }

    public WaitingList getWaitingList() {
        return waitingList;
    }

    private synchronized void getOut() {
        ArrayList<MyRequest> outList = inside.requestOutFloor(Tool.numberToFloor(currentFloor));
        ArrayList<MyRequest> forcedOutList = inside.getContent();
        if (status != Status.OPENING) {
            TimableOutput.println("OPEN-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
            status = Status.OPENING;
        }
        for (MyRequest myRequest : outList) {
            TimableOutput.println("OUT-" + myRequest.getPersonId()
                + "-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
        }
        for (MyRequest myRequest : forcedOutList) {
            TimableOutput.println("OUT-" + myRequest.getPersonId()
                + "-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
        }
        for (MyRequest myRequest : forcedOutList) {
            myRequest.setPresentFloor(Tool.numberToFloor(currentFloor));
            waitingList.add(myRequest);
        }
        inside.clear();
    }

    private synchronized void getIn(Status dir) {
        ArrayList<MyRequest> inList =
            waitingList.requestInFloor(Tool.numberToFloor(currentFloor),6 - inside.size(), dir);
        if (status != Status.OPENING) {
            TimableOutput.println("OPEN-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
            status = Status.OPENING;
        }
        for (MyRequest myRequest : inList) {
            inside.add(myRequest);
            TimableOutput.println("IN-" + myRequest.getPersonId()
                + "-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
        }
    }

    private synchronized void move(Advice advice) {
        if (advice == Advice.REVERSE) {
            direction = Tool.reverse(direction);
            if (waitingList.needIn(currentFloor, direction)
                || waitingList.needIn(currentFloor, Tool.reverse(direction))) {
                getOut();
                getIn(direction);
                getIn(Tool.reverse(direction));
                try {
                    sleep(400);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
                TimableOutput.println("CLOSE-"
                    + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
                status = Status.MOVING;
            }
        }
        if (status == Status.OPENING) {
            try {
                sleep(400);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            TimableOutput.println("CLOSE-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
            status = Status.MOVING;
        }
        try {
            sleep(400);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        if (direction == Status.UP) {
            ++currentFloor;
        }
        else if (direction == Status.DOWN) {
            --currentFloor;
        }
        TimableOutput.println("ARRIVE-" + Tool.numberToFloor(currentFloor) + "-" + elevatorId);
    }
}
