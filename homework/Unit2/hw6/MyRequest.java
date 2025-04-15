import com.oocourse.elevator2.PersonRequest;

public class MyRequest extends PersonRequest {
    private String presentFloor;

    public MyRequest(String fromFloor, String toFloor, int personId, int priority) {
        super(fromFloor, toFloor, personId, priority);
        presentFloor = fromFloor;
    }

    public MyRequest(PersonRequest personRequest) {
        super(personRequest.getFromFloor(),
            personRequest.getToFloor(),
            personRequest.getPersonId(),
            personRequest.getPriority());
        presentFloor = personRequest.getFromFloor();
    }

    public String getPresentFloor() {
        return presentFloor;
    }

    public void setPresentFloor(String presentFloor) {
        this.presentFloor = presentFloor;
    }
}
