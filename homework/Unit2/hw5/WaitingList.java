import java.util.ArrayList;

public class WaitingList {
    private ArrayList<MyRequest> waitingList = new ArrayList<>();

    public ArrayList<MyRequest> getContent() {
        return waitingList;
    }

    public synchronized void add(MyRequest person) {
        waitingList.add(person);
    }

    public synchronized void remove(MyRequest person) {
        waitingList.remove(person);
    }

    public synchronized MyRequest get(int number) {
        return waitingList.get(number);
    }

    public synchronized int size() {
        return waitingList.size();
    }

    public synchronized boolean isEmpty() {
        return waitingList.isEmpty();
    }

    public synchronized boolean needOut(int floor) {
        for (MyRequest person : waitingList) {
            if (person.getToFloor().equals(Tool.numberToFloor(floor))) {
                return true;
            }
        }
        return false;
    }

    public synchronized boolean needIn(int floor,Status direction) {
        for (MyRequest person : waitingList) {
            if (person.getPresentFloor().equals(Tool.numberToFloor(floor))
                && Tool.getDir(person) == direction) {
                return true;
            }
        }
        return false;
    }

    public synchronized void clear() {
        waitingList.clear();
    }

    public synchronized ArrayList<MyRequest>
        requestInFloor(String floor,int number,Status direction) {
        ArrayList<MyRequest> requests = new ArrayList<>();
        for (MyRequest person : waitingList) {
            if (person.getPresentFloor().equals(floor) && Tool.getDir(person) == direction) {
                requests.add(person);
            }
        }
        int size = requests.size();
        for (int i = 0;i < size - number;i++) {
            int minPriority = Integer.MAX_VALUE;
            for (int j = 0;j < requests.size();j++) {
                if (requests.get(j).getPriority() < minPriority) {
                    minPriority = requests.get(j).getPriority();
                }
            }
            for (int j = 0;j < requests.size();j++) {
                if (requests.get(j).getPriority() == minPriority) {
                    requests.remove(j);
                    break;
                }
            }
        }
        for (MyRequest person : requests) {
            waitingList.remove(person);
        }
        return requests;
    }

    public synchronized ArrayList<MyRequest> requestOutFloor(String floor) {
        ArrayList<MyRequest> requests = new ArrayList<>();
        for (MyRequest person : waitingList) {
            if (person.getToFloor().equals(floor)) {
                requests.add(person);
            }
        }
        for (MyRequest person : requests) {
            waitingList.remove(person);
        }
        return requests;
    }

    public boolean checkToRequestUp(int floor) {
        for (MyRequest person : waitingList) {
            if (Tool.floorToNumber(person.getToFloor()) > floor) {
                return true;
            }
        }
        return false;
    }

    public boolean checkToRequestDown(int floor) {
        for (MyRequest person : waitingList) {
            if (Tool.floorToNumber(person.getToFloor()) < floor) {
                return true;
            }
        }
        return false;
    }

    public synchronized boolean checkPresentRequestUp(int floor) {
        for (MyRequest person : waitingList) {
            if (Tool.floorToNumber(person.getPresentFloor()) > floor) {
                return true;
            }
        }
        return false;
    }

    public synchronized boolean checkPresentRequestDown(int floor) {
        for (MyRequest person : waitingList) {
            if (Tool.floorToNumber(person.getPresentFloor()) < floor) {
                return true;
            }
        }
        return false;
    }
}
