//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

import com.oocourse.elevator3.ScheRequest;
import com.oocourse.elevator3.TimableOutput;
import com.oocourse.elevator3.UpdateRequest;

import java.util.ArrayList;
import java.util.concurrent.locks.ReentrantLock;

public class Elevator extends Thread {
    private final int elevatorId;
    private int currentFloor;
    private boolean isEnd = false;
    private Status status;
    private Status direction;
    private final WaitingList waitingList = new WaitingList();
    private final WaitingList inside = new WaitingList();
    private final Strategy strategy;
    private double speed;
    private Boolean isValid;
    private final Distributor distributor;
    private final Object validLock = new Object();
    private int topFloor;
    private int bottomFloor;
    private Elevator twinElevator = null;
    private ArrayList<Elevator> elevators;
    private boolean updateReady = false;
    private final Object updateReadyLock = new Object();
    private final Object currentFloorLock = new Object();
    private int elevatorKind = 0;
    private ReentrantLock sharedFloorLock = new ReentrantLock();
    private int sharedFloor = 0;
    // 1  : upElevator
    // -1 : downElevator
    // 0  : normalElevator

    public ReentrantLock getSharedFloorLock() {
        return sharedFloorLock;
    }

    public int getKind() {
        return elevatorKind;
    }

    public int getCurrentFloor() {
        synchronized (currentFloorLock) {
            return currentFloor;
        }
    }

    public Object getCurrentFloorLock() {
        return currentFloorLock;
    }

    public int getTwinPos() {
        synchronized (twinElevator.getCurrentFloorLock()) {
            return twinElevator.getCurrentFloor();
        }
    }

    public void setUpdateReady() {
        synchronized (updateReadyLock) {
            updateReady = true;
        }
    }

    public Boolean updated() {
        synchronized (updateReadyLock) {
            return updateReady;
        }
    }

    public int totalSize() {
        return waitingList.size() + inside.size();
    }

    public Object getValidLock() {
        return validLock;
    }

    public void setValid() {
        synchronized (validLock) {
            isValid = true;
        }
    }

    public void setInvalid() {
        synchronized (validLock) {
            isValid = false;
        }
    }

    public Boolean isValid() {
        synchronized (validLock) {
            return isValid;
        }
    }

    public Elevator(int elevatorId, Distributor distributor) {
        strategy = new Strategy(this.waitingList, this.inside, this);
        speed = 0.4;
        setValid();
        this.elevatorId = elevatorId;
        status = Status.WAITING;
        direction = Status.UP;
        currentFloor = 1;
        this.distributor = distributor;
        topFloor = 7;
        bottomFloor = -3;
        elevators = distributor.getElevators();
    }

    public int getElevatorId() {
        return this.elevatorId;
    }

    public void setIsEnd() {
        this.isEnd = true;
    }

    public void run() {
        while (true) {
            Advice advice;
            synchronized (this.waitingList) {
                advice = this.strategy.getAdvice(this.currentFloor, this.status, this.direction);
                if (Debug.d()) {
                    System.out.println("[LOG] Elevator " +
                        this.elevatorId + " get advice : " + advice.toString());
                }
            }
            if (advice == Advice.SCHE) {
                this.scheduledEvent(this.waitingList.getScheRequest());
            }
            if (advice == Advice.UPDATE) {
                updateEvent(waitingList.getUpdateRequest());
            }
            if (advice == Advice.MOVE || advice == Advice.REVERSE) {
                this.move(advice);
            }
            if (advice == Advice.OPEN) {
                this.getOut();
                this.getIn(this.direction);
                if (this.inside.isEmpty() &&
                    this.waitingList.needIn(this.currentFloor, Tool.reverse(this.direction))) {
                    synchronized (this.waitingList) {
                        this.getIn(Tool.reverse(this.direction));
                    }

                    this.direction = Tool.reverse(this.direction);
                }
                Tool.goodSleep(400);
                this.getIn(this.direction);
                TimableOutput.println("CLOSE-" +
                    Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
                this.status = Status.MOVING;
            }
            while (advice == Advice.WAIT) {
                synchronized (this.waitingList) {
                    this.status = Status.WAITING;
                    if (this.isEnd) {
                        return;
                    }
                    try {
                        if (Debug.d()) {
                            System.out.println("[LOG] Elevator: " + elevatorId + " is waiting");
                        }
                        this.waitingList.wait(5000);
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                    advice = this.strategy.getAdvice(this.currentFloor,
                            this.status, this.direction);
                }
            }
        }
    }

    public WaitingList getWaitingList() {
        return this.waitingList;
    }

    private void getOut() {
        ArrayList<MyRequest> outList =
            this.inside.requestOutFloor(Tool.numberToFloor(this.currentFloor));
        ArrayList<MyRequest> forcedOutList = this.inside.getContent();
        if (this.status != Status.OPENING) {
            TimableOutput.println("OPEN-" +
                Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
            this.status = Status.OPENING;
        }

        for (MyRequest myRequest : outList) {
            TimableOutput.println("OUT-S-" +
                myRequest.getPersonId() + "-" +
                Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
            this.distributor.requestOver();
            WaitingList plate = this.distributor.getPlate();
            synchronized (plate) {
                plate.notifyAll();
            }
        }

        WaitingList plate = this.distributor.getPlate();

        for (MyRequest myRequest : forcedOutList) {
            TimableOutput.println("OUT-F-" +
                myRequest.getPersonId() + "-" +
                Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
            synchronized (plate) {
                plate.add(myRequest);
                myRequest.setPresentFloor(Tool.numberToFloor(this.currentFloor));
            }
        }

        if (!forcedOutList.isEmpty()) {
            synchronized (plate) {
                plate.notifyAll();
            }
        }

        this.inside.clear();
    }

    private void getIn(Status dir) {
        ArrayList<MyRequest> inList = new ArrayList<>();
        synchronized (waitingList) {
            inList = this.waitingList.requestInFloor(Tool.numberToFloor(this.currentFloor),
                    6 - this.inside.size(), dir);
        }
        if (this.status != Status.OPENING) {
            TimableOutput.println("OPEN-" +
                Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
            this.status = Status.OPENING;
        }
        for (MyRequest myRequest : inList) {
            this.inside.add(myRequest);
            TimableOutput.println("IN-" + myRequest.getPersonId() +
                "-" + Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
        }

    }

    private void move(Advice advice) {
        if (advice == Advice.REVERSE) {
            this.direction = Tool.reverse(this.direction);
            if (isValid() && (this.waitingList.needIn(this.currentFloor, this.direction)
                || this.waitingList.needIn(this.currentFloor, Tool.reverse(this.direction)))) {
                this.getOut();
                this.getIn(this.direction);
                this.getIn(Tool.reverse(this.direction));
                Tool.goodSleep(400);
                TimableOutput.println("CLOSE-" +
                    Tool.numberToFloor(this.currentFloor) + "-" + this.elevatorId);
                this.status = Status.MOVING;
            }
        }
        boolean needUnlock = false;
        if (direction == Status.UP && elevatorKind == -1 && currentFloor + 1 == topFloor) {
            sharedFloorLock.lock();
        }
        if (direction == Status.DOWN && elevatorKind == 1 && currentFloor - 1 == bottomFloor) {
            sharedFloorLock.lock();
        }
        if (inSharedFloor()) {
            needUnlock = true;
        }
        if (this.status == Status.OPENING) {
            Tool.goodSleep(400);
            TimableOutput.println("CLOSE-" + Tool.numberToFloor(this.currentFloor) +
                "-" + this.elevatorId);
            this.status = Status.MOVING;
        }
        if (this.direction == Status.UP) {
            ++this.currentFloor;
            for (MyRequest myRequest : this.inside.getContent()) {
                myRequest.setPresentFloor(Tool.numberToFloor(this.currentFloor));
            }
        } else if (this.direction == Status.DOWN) {
            --this.currentFloor;
            for (MyRequest myRequest : this.inside.getContent()) {
                myRequest.setPresentFloor(Tool.numberToFloor(this.currentFloor));
            }
        }
        Tool.goodSleep((long)((double)1000.0F * this.speed));
        TimableOutput.println("ARRIVE-" + Tool.numberToFloor(this.currentFloor) +
            "-" + this.elevatorId);
        if (needUnlock) {
            sharedFloorLock.unlock();
        }
    }

    private void scheduledEvent(ScheRequest sche) {
        this.speed = sche.getSpeed();
        int toFloor = Tool.floorToNumber(sche.getToFloor());
        this.getIn(Tool.getDir(this.currentFloor, toFloor));
        if (this.status == Status.OPENING) {
            Tool.goodSleep(400);
            TimableOutput.println("CLOSE-" + Tool.numberToFloor(this.currentFloor) +
                "-" + this.elevatorId);
            this.status = Status.MOVING;
        }
        synchronized (validLock) {
            TimableOutput.println("SCHE-BEGIN-" + this.elevatorId);
            setInvalid();
        }
        while (this.currentFloor != toFloor) {
            if (this.direction == Tool.getDir(this.currentFloor, toFloor)) {
                this.move(Advice.MOVE);
            } else {
                this.move(Advice.REVERSE);
            }
        }
        TimableOutput.println("OPEN-" + Tool.numberToFloor(this.currentFloor) +
            "-" + this.elevatorId);
        this.status = Status.OPENING;
        this.getOut();
        WaitingList plate = this.distributor.getPlate();
        for (MyRequest request : this.waitingList.getContent()) {
            synchronized (plate) {
                plate.add(request);
            }
        }
        if (!this.waitingList.needIn(this.currentFloor, this.direction)) {
            synchronized (plate) {
                plate.notifyAll();
            }
        }
        this.waitingList.clear();
        Tool.goodSleep(1000);
        TimableOutput.println("CLOSE-" + Tool.numberToFloor(this.currentFloor) +
            "-" + this.elevatorId);
        this.status = Status.MOVING;
        TimableOutput.println("SCHE-END-" + this.elevatorId);
        setValid();
        synchronized (distributor.getPlate()) {
            distributor.getPlate().notifyAll();
        }
        this.speed = 0.4;
    }

    public int getDistance(int floor) {
        if (floor == this.currentFloor) {
            return 0;
        } else if (floor > this.currentFloor) {
            return this.direction == Status.UP ? floor - this.currentFloor :
                floor - this.currentFloor + 2 * (this.currentFloor + 2);
        } else {
            return this.direction == Status.UP ? this.currentFloor - floor +
                2 * (7 - this.currentFloor) : this.currentFloor - floor;
        }
    }

    private void updateEvent(UpdateRequest update) {
        if (!inside.isEmpty()) {
            getOut();
            if (status == Status.OPENING) {
                Tool.goodSleep(400);
                TimableOutput.println("CLOSE-" + Tool.numberToFloor(this.currentFloor) +
                    "-" + this.elevatorId);
                this.status = Status.MOVING;
            }
        }
        speed = 0.2;
        if (Debug.d()) {
            System.out.println("[LOG]elevator " + elevatorId + " start an update event");
        }
        if (elevatorId == update.getElevatorAId()) {
            setUpdateReady();
            twinElevator = elevators.get(update.getElevatorBId() - 1);
            setInvalid();
            do {
                Tool.goodSleep(30);
            } while (!twinElevator.updated());
            putEverythingBack();
            sharedFloorLock = twinElevator.getSharedFloorLock();
            currentFloor = Tool.floorToNumber(update.getTransferFloor()) + 1;
            sharedFloor = Tool.floorToNumber(update.getTransferFloor());
            topFloor = 7;
            elevatorKind = 1;
            bottomFloor = Tool.floorToNumber(update.getTransferFloor());
            Tool.goodSleep(1000);
        }
        else {
            twinElevator = elevators.get(update.getElevatorAId() - 1);
            do {
                Tool.goodSleep(30);
            } while (!twinElevator.updated());
            setInvalid();
            TimableOutput.println("UPDATE-BEGIN-" +
                update.getElevatorAId() + "-" + update.getElevatorBId());
            putEverythingBack();
            setUpdateReady();
            currentFloor = Tool.floorToNumber(update.getTransferFloor()) - 1;
            topFloor = Tool.floorToNumber(update.getTransferFloor());
            sharedFloor = Tool.floorToNumber(update.getTransferFloor());
            bottomFloor = -3;
            elevatorKind = -1;
            Tool.goodSleep(1000);
            TimableOutput.println("UPDATE-END-" +
                update.getElevatorAId() + "-" + update.getElevatorBId());
        }
        setValid();
        if (Debug.d()) {
            System.out.println("[LOG] elevator " + elevatorId +
                " end an update event, now request in it : " + waitingList.size() + inside.size());
        }
    }

    public boolean reachTop() {
        if (direction == Status.UP) {
            if (currentFloor == topFloor) {
                return true;
            }
            return false;
        } else {
            if (currentFloor == bottomFloor) {
                return true;
            }
            return false;
        }
    }

    public boolean inSharedFloor() {
        if (bottomFloor == currentFloor && elevatorKind == 1) {
            return true;
        }
        if (topFloor == currentFloor && elevatorKind == -1) {
            return true;
        }
        return false;
    }

    public boolean needOut(int floor) {
        if (inside.needOut(floor)) {
            return true;
        }
        if (elevatorKind == -1 && floor == topFloor) {
            if (inside.haveRequestBetween(topFloor, 7)) {
                return true;
            }
        }
        if (elevatorKind == 1 && floor == bottomFloor) {
            if (inside.haveRequestBetween(-3, bottomFloor)) {
                return true;
            }
        }
        return false;
    }

    public boolean fitRequest(MyRequest request) {
        synchronized (validLock) {
            if (!isValid) {
                return false;
            }
        }
        int presentFloor = Tool.floorToNumber(request.getPresentFloor());
        if (presentFloor > topFloor || presentFloor < bottomFloor) {
            return false;
        }
        if (presentFloor == sharedFloor) {
            if (Tool.getDir(request) == Status.UP && elevatorKind == -1) {
                return false;
            }
            if (Tool.getDir(request) == Status.DOWN && elevatorKind == 1) {
                return false;
            }
        }
        return true;
    }

    public void putEverythingBack() {
        WaitingList plate = this.distributor.getPlate();
        for (MyRequest request : this.waitingList.getContent()) {
            synchronized (plate) {
                plate.add(request);
            }
        }
        waitingList.clear();
    }
}
