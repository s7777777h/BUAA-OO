//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

import com.oocourse.elevator3.PersonRequest;

public class MyRequest extends PersonRequest {
    private String presentFloor;

    public MyRequest(PersonRequest personRequest) {
        super(personRequest.getFromFloor(),
            personRequest.getToFloor(),
            personRequest.getPersonId(),
            personRequest.getPriority());
        this.presentFloor = personRequest.getFromFloor();
    }

    public String getPresentFloor() {
        return this.presentFloor;
    }

    public void setPresentFloor(String presentFloor) {
        this.presentFloor = presentFloor;
    }
}
