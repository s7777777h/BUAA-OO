//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

import com.oocourse.elevator3.TimableOutput;
import com.oocourse.elevator3.ElevatorInput;
import com.oocourse.elevator3.Request;
import com.oocourse.elevator3.PersonRequest;
import com.oocourse.elevator3.ScheRequest;
import com.oocourse.elevator3.UpdateRequest;

class Main {
    Main() {
    }

    public static void main(String[] args) throws Exception {
        Distributor distributor = new Distributor();
        TimableOutput.initStartTimestamp();
        ElevatorInput elevatorInput = new ElevatorInput(System.in);
        distributor.start();

        while (true) {
            Request request = elevatorInput.nextRequest();
            if (request == null) {
                synchronized (distributor.getPlate()) {
                    distributor.getPlate().notify();
                }
                distributor.inputEnd();
                if (Debug.d()) {
                    System.out.println("[LOG]Elevator input has been closed");
                }
                elevatorInput.close();
                return;
            }
            if (request instanceof PersonRequest) {
                PersonRequest personRequest = (PersonRequest)request;
                MyRequest myRequest = new MyRequest(personRequest);
                WaitingList plate = distributor.getPlate();
                distributor.getRequest();
                synchronized (plate) {
                    plate.add(myRequest);
                    plate.notifyAll();
                }
            }
            if (request instanceof ScheRequest) {
                ScheRequest scheRequest = (ScheRequest)request;
                WaitingList plate = distributor.getPlate();
                synchronized (plate) {
                    plate.addScheRequest(scheRequest);
                    plate.notifyAll();
                }
            }
            if (request instanceof UpdateRequest) {
                UpdateRequest updateRequest = (UpdateRequest)request;
                WaitingList plate = distributor.getPlate();
                synchronized (plate) {
                    plate.addUpdateRequest(updateRequest);
                    plate.notifyAll();
                }
            }
        }
    }
}
