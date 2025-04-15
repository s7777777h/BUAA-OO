import com.oocourse.elevator1.PersonRequest;

public class MyRequest extends PersonRequest {
    private String presentFloor;

    public MyRequest(String fromFloor, String toFloor, int personId, int priority, int elevatorId) {
        super(fromFloor, toFloor, personId, priority, elevatorId);
        presentFloor = fromFloor;
    }

    public MyRequest(PersonRequest personRequest) {
        super(personRequest.getFromFloor(),
            personRequest.getToFloor(),
            personRequest.getPersonId(),
            personRequest.getPriority(),
            personRequest.getElevatorId());
        presentFloor = personRequest.getFromFloor();
    }

    public String getPresentFloor() {
        return presentFloor;
    }

    public void setPresentFloor(String presentFloor) {
        this.presentFloor = presentFloor;
    }
}
