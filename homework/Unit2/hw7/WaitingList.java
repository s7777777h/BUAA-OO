//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

import com.oocourse.elevator3.ScheRequest;
import com.oocourse.elevator3.UpdateRequest;

import java.util.ArrayList;

public class WaitingList {
    private final ArrayList<MyRequest> waitingList = new ArrayList<>();
    private final ArrayList<ScheRequest> scheList = new ArrayList<>();
    private final ArrayList<UpdateRequest> updateList = new ArrayList<>();

    public boolean haveDir(Status direction) {
        for (MyRequest myRequest : waitingList) {
            if (Tool.getDir(myRequest) == direction) {
                return true;
            }
        }
        return false;
    }

    public synchronized boolean haveSchedule() {
        return !this.scheList.isEmpty();
    }

    public synchronized boolean haveWaitingList() {
        return !this.waitingList.isEmpty();
    }

    public synchronized boolean haveUpdateList() {
        return !this.updateList.isEmpty();
    }

    public synchronized void addScheRequest(ScheRequest sche) {
        this.scheList.add(sche);
    }

    public synchronized void addUpdateRequest(UpdateRequest update) {
        this.updateList.add(update);
    }

    public synchronized ScheRequest getScheRequest() {
        if (!this.scheList.isEmpty()) {

            return this.scheList.remove(0);
        }
        return null;
    }

    public synchronized UpdateRequest getUpdateRequest() {
        if (!this.updateList.isEmpty()) {
            return this.updateList.remove(0);
        }
        return null;
    }

    public ArrayList<MyRequest> getContent() {
        return this.waitingList;
    }

    public synchronized void add(MyRequest person) {
        this.waitingList.add(person);
    }

    public synchronized void remove(MyRequest person) {
        this.waitingList.remove(person);
    }

    public synchronized MyRequest get() {
        return this.waitingList.remove(0);
    }

    public synchronized int size() {
        return this.waitingList.size();
    }

    public synchronized boolean isEmpty() {
        return this.waitingList.isEmpty()
            && this.scheList.isEmpty()
            && this.updateList.isEmpty();
    }

    public synchronized boolean needOut(int floor) {
        for (MyRequest person : this.waitingList) {
            if (person.getToFloor().equals(Tool.numberToFloor(floor))) {
                return true;
            }
        }

        return false;
    }

    public synchronized boolean haveRequestBetween(int bottomFloor, int topFloor) {
        for (MyRequest person : this.waitingList) {
            int toFloor = Tool.floorToNumber(person.getToFloor());
            if (toFloor >= bottomFloor && toFloor <= topFloor) {
                return true;
            }
        }
        return false;
    }

    public synchronized boolean needIn(int floor, Status direction) {
        for (MyRequest person : this.waitingList) {
            if (person.getPresentFloor().equals(Tool.numberToFloor(floor))
                && Tool.getDir(person) == direction) {
                return true;
            }
        }

        return false;
    }

    public synchronized void clear() {
        this.waitingList.clear();
    }

    public synchronized ArrayList<MyRequest> requestInFloor(String floor,
        int number, Status direction) {
        ArrayList<MyRequest> requests = new ArrayList<>();
        for (MyRequest person : this.waitingList) {
            if (person.getPresentFloor().equals(floor) && Tool.getDir(person) == direction) {
                requests.add(person);
            }
        }
        int size = requests.size();
        for (int i = 0; i < size - number; ++i) {
            int minPriority = Integer.MAX_VALUE;
            for (MyRequest request : requests) {
                if (request.getPriority() < minPriority) {
                    minPriority = request.getPriority();
                }
            }
            for (int j = 0; j < requests.size(); ++j) {
                if ((requests.get(j)).getPriority() == minPriority) {
                    requests.remove(j);
                    break;
                }
            }
        }

        for (MyRequest person : requests) {
            this.waitingList.remove(person);
        }

        return requests;
    }

    public synchronized ArrayList<MyRequest> requestOutFloor(String floor) {
        ArrayList<MyRequest> requests = new ArrayList<>();
        for (MyRequest person : this.waitingList) {
            if (person.getToFloor().equals(floor)) {
                requests.add(person);
            }
        }

        for (MyRequest person : requests) {
            this.waitingList.remove(person);
        }

        return requests;
    }

    public synchronized boolean checkPresentRequestUp(int floor) {
        for (MyRequest person : this.waitingList) {
            if (Tool.floorToNumber(person.getPresentFloor()) > floor) {
                return true;
            }
        }

        return false;
    }

    public synchronized boolean checkPresentRequestDown(int floor) {
        for (MyRequest person : this.waitingList) {
            if (Tool.floorToNumber(person.getPresentFloor()) < floor) {
                return true;
            }
        }

        return false;
    }
}
