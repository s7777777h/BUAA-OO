import java.util.ArrayList;

public class Distributor extends Thread {
    private ArrayList<Elevator> elevators = new ArrayList<>();
    private WaitingList wait = new WaitingList();
    private boolean isEnd = false;

    public WaitingList getWaiting() {
        return wait;
    }

    public void setIsEnd() {
        this.isEnd = true;
    }

    public void run() {
        for (int i = 1;i <= 6;++i) {
            Elevator newElevator = new Elevator(i);
            elevators.add(newElevator);
            newElevator.start();
        }
        synchronized (wait) {
            while (true) {
                if (isEnd && wait.isEmpty()) {
                    for (Elevator elevator : elevators) {
                        elevator.setIsEnd();
                        WaitingList temp = elevator.getWaitingList();
                        synchronized (temp) {
                            temp.notifyAll();
                        }
                    }
                    if (Debug.d()) {
                        System.out.println("Distributor end");
                    }
                    return;
                }
                try {
                    wait.wait();
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
                if (wait.isEmpty()) {
                    for (Elevator elevator : elevators) {
                        elevator.setIsEnd();
                        WaitingList temp = elevator.getWaitingList();
                        synchronized (temp) {
                            temp.notifyAll();
                        }
                    }
                    if (Debug.d()) {
                        System.out.println("Distributor end");
                    }
                    return;
                }
                while (!wait.isEmpty()) {
                    MyRequest request = wait.get(0);
                    wait.remove(request);
                    int elevatorId = request.getElevatorId();
                    Elevator elevator = elevators.get(elevatorId - 1);
                    if (Debug.d()) {
                        System.out.println(elevatorId + " get " + request.getPersonId());
                    }
                    WaitingList waitingList = elevator.getWaitingList();
                    synchronized (waitingList) {
                        waitingList.add(request);
                        waitingList.notifyAll();
                    }
                }
            }
        }
    }

    public WaitingList getWait() {
        return wait;
    }
}
