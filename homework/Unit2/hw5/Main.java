import com.oocourse.elevator1.TimableOutput;
import com.oocourse.elevator1.ElevatorInput;
import com.oocourse.elevator1.PersonRequest;
import com.oocourse.elevator1.Request;

class Main {
    public static void main(String[] args) throws Exception {
        Distributor distributor = new Distributor();
        TimableOutput.initStartTimestamp();
        ElevatorInput elevatorInput = new ElevatorInput(System.in);
        distributor.start();
        while (true) {
            Request request = elevatorInput.nextRequest();
            // when request == null
            // it means there are no more lines in stdin
            if (request == null) {
                synchronized (distributor.getWaiting()) {
                    distributor.getWaiting().notify();
                }
                distributor.setIsEnd();
                if (Debug.d()) {
                    System.out.println("Elevator input has been closed");
                }
                break;
            } else {
                // a new valid request
                if (request instanceof PersonRequest) {
                    PersonRequest personRequest = (PersonRequest) request;
                    MyRequest myRequest = new MyRequest(personRequest);
                    WaitingList wait = distributor.getWait();
                    synchronized (wait) {
                        wait.add(myRequest);
                        wait.notifyAll();
                    }
                }
            }
        }
        elevatorInput.close();
    }
}