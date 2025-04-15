import com.oocourse.elevator3.ScheRequest;
import com.oocourse.elevator3.TimableOutput;
import com.oocourse.elevator3.UpdateRequest;

import java.util.ArrayList;
import java.util.Random;

public class Distributor extends Thread {
    private final ArrayList<Elevator> elevators = new ArrayList<>();
    private final WaitingList plate = new WaitingList();
    private boolean inputEnd = false;
    private int remainingRequest = 0;
    private final Object remainingRequestLock = new Object();

    public ArrayList<Elevator> getElevators() {
        return elevators;
    }

    public void requestOver() {
        synchronized (remainingRequestLock) {
            --this.remainingRequest;
        }
        if (Debug.d()) {
            System.out.println("[LOG] a request over, present request: " + remainingRequest);
        }
    }

    public void getRequest() {
        synchronized (remainingRequestLock) {
            ++this.remainingRequest;
        }
    }

    public void inputEnd() {
        this.inputEnd = true;
    }

    public void run() {
        if (Debug.d()) {
            System.out.print("[LOG]");
            TimableOutput.println("distributor started");
        }
        for (int i = 1; i <= 6; ++i) {
            Elevator newElevator = new Elevator(i, this);
            this.elevators.add(newElevator);
            newElevator.start();
        }
        while (true) {
            if (checkEnd()) {
                return;
            }
            while (!this.plate.isEmpty() && !this.allElevatorsInvalid()) {
                boolean flag;
                synchronized (plate) {
                    flag = plate.haveUpdateList();
                }
                if (flag) {
                    if (Debug.d()) {
                        System.out.println("[LOG] distribute updates");
                    }
                    distributeUpdateRequest();
                }
                synchronized (plate) {
                    flag = plate.haveSchedule();
                }
                if (flag) {
                    distributeScheRequest();
                    if (Debug.d()) {
                        System.out.println("[LOG] distribute scheduling");
                    }
                }
                synchronized (plate) {
                    flag = plate.haveWaitingList();
                }
                if (flag) {
                    distributeMyRequest();
                    if (Debug.d()) {
                        System.out.println("[LOG] distribute myrequest");
                    }
                }
                Tool.goodSleep(50);
            }
        }
    }

    private void distributeMyRequest() {
        MyRequest request;
        synchronized (this.plate) {
            request = this.plate.get();
        }
        int elevatorId = weight_random_distribute(request);
        if (elevatorId == 0) {
            return;
        }
        Elevator elevator = this.elevators.get(elevatorId - 1);
        boolean success = false;
        synchronized (elevator.getValidLock()) {
            if (elevator.isValid()) {
                TimableOutput.println("RECEIVE-" +
                    request.getPersonId() + "-" + elevatorId);
                success = true;
            }
        }
        if (success) {
            WaitingList temp = elevator.getWaitingList();
            synchronized (temp) {
                temp.add(request);
                temp.notifyAll();
            }
        }
        if (!success) {
            plate.add(request);
        }
    }

    private void distributeScheRequest() {
        ScheRequest sche;
        synchronized (this.plate) {
            sche = this.plate.getScheRequest();
        }
        int elevatorID = sche.getElevatorId();
        Elevator elevator = this.elevators.get(elevatorID - 1);
        WaitingList temp = elevator.getWaitingList();
        synchronized (temp) {
            temp.addScheRequest(sche);
            temp.notifyAll();
        }
    }

    private void distributeUpdateRequest() {
        UpdateRequest update;
        synchronized (this.plate) {
            update = this.plate.getUpdateRequest();
        }
        int elevatorAId = update.getElevatorAId();
        int elevatorBId = update.getElevatorBId();
        Elevator elevatorA = this.elevators.get(elevatorAId - 1);
        Elevator elevatorB = this.elevators.get(elevatorBId - 1);
        WaitingList alist = elevatorA.getWaitingList();
        WaitingList blist = elevatorB.getWaitingList();
        synchronized (alist) {
            alist.addUpdateRequest(update);
            alist.notifyAll();
        }
        synchronized (blist) {
            blist.addUpdateRequest(update);
            blist.notifyAll();
        }

    }

    private boolean noRequest() {
        synchronized (remainingRequestLock) {
            return this.remainingRequest == 0;
        }
    }

    private boolean checkEnd() {
        synchronized (this.plate) {
            if (this.inputEnd && this.plate.isEmpty() && noRequest()) {
                this.getEnd();
                return true;
            }
            try {
                this.plate.wait(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        synchronized (this.plate) {
            if (this.plate.isEmpty() && this.remainingRequest == 0 && this.inputEnd) {
                this.getEnd();
                return true;
            }
        }
        return false;
    }

    public WaitingList getPlate() {
        return this.plate;
    }

    private int weight_random_distribute(MyRequest request) {
        ArrayList<Elevator> temp = new ArrayList<>();
        ArrayList<Elevator> chooseList = new ArrayList<>();
        for (Elevator elevator : this.elevators) {
            if (elevator.isValid()) {
                temp.add(elevator);
            }
        }
        for (Elevator elevator : temp) {
            int elevatorWeight = update_weight(request, elevator);
            for (int i = 0;i <= elevatorWeight; i++) {
                chooseList.add(elevator);
            }
        }
        Random rand = new Random();
        return chooseList.get(rand.nextInt(chooseList.size())).getElevatorId();
    }

    private int distance_weight(MyRequest request, Elevator elevator) {
        return (20 - elevator.getDistance(Tool.floorToNumber(request.getPresentFloor()))) / 5;
    }

    private int update_weight(MyRequest request, Elevator elevator) {
        return distance_weight(request, elevator) *
            (elevator.getKind() == 0 ? 1 : 2);
    }

    private int distance_distribute(MyRequest request) {
        ArrayList<Elevator> temp = new ArrayList<>();
        for (Elevator elevator : this.elevators) {
            if (elevator.isValid()) {
                temp.add(elevator);
            }
        }
        int minDistance = Integer.MAX_VALUE;
        int returnVal = 0;
        for (Elevator elevator : temp) {
            if (elevator.isValid() && elevator.fitRequest(request)) {
                int floorNumber = Tool.floorToNumber(request.getPresentFloor());
                if (elevator.getDistance(floorNumber) < minDistance) {
                    minDistance = elevator.getDistance(floorNumber);
                    returnVal = elevator.getElevatorId();
                }
            }
        }
        return returnVal;
    }

    private int weight_distribute(MyRequest request) {
        ArrayList<Elevator> temp = new ArrayList<>();
        for (Elevator elevator : this.elevators) {
            if (elevator.isValid() && elevator.fitRequest(request)) {
                temp.add(elevator);
            }
        }
        Double minVal = Double.MAX_VALUE;
        int returnVal = 0;
        double w = 0.2;
        for (Elevator elevator : temp) {
            if (elevator.isValid()) {
                int floorNumber = Tool.floorToNumber(request.getPresentFloor());
                double tmp = elevator.getDistance(floorNumber) + w * elevator.totalSize();
                if (tmp < minVal) {
                    minVal = tmp;
                    returnVal = elevator.getElevatorId();
                }
            }
        }
        return returnVal;
    }

    private int rand_distribute(MyRequest request) {
        ArrayList<Elevator> temp = new ArrayList<>();

        for (Elevator elevator : this.elevators) {
            if (elevator.isValid() && elevator.fitRequest(request)) {
                temp.add(elevator);
            }
        }

        Random rand = new Random();
        int randNum = rand.nextInt(temp.size());
        return (temp.get(randNum)).getElevatorId();
    }

    private boolean allElevatorsInvalid() {
        boolean result = false;
        for (Elevator elevator : this.elevators) {
            result |= elevator.isValid();
        }
        if (Debug.d()) {
            System.out.println("[LOG]invalid status: " + !result);
        }
        return !result;
    }

    private void getEnd() {
        for (Elevator elevator : this.elevators) {
            elevator.setIsEnd();
            WaitingList temp = elevator.getWaitingList();
            synchronized (temp) {
                temp.notifyAll();
            }
        }
        if (Debug.d()) {
            System.out.println("[LOG]Distributor end");
        }
    }
}
