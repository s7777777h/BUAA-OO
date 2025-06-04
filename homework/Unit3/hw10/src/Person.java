import com.oocourse.spec2.exceptions.AcquaintanceNotFoundException;
import com.oocourse.spec2.main.PersonInterface;
import com.oocourse.spec2.main.TagInterface;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import static java.lang.Math.min;

public class Person implements PersonInterface {
    private final int id;
    private final String name;
    private final int age;
    private int bestAcquaintanceId = -1;
    private int bestAcquaintanceValue = -100000;
    private final HashMap<Integer, PersonInterface> acquaintance = new HashMap<>();
    private final HashMap<Integer, Integer> value = new HashMap<>();
    private final HashMap<Integer, TagInterface> tags = new HashMap<>();
    private final HashMap<Integer, ArrayList<ListItem>> receivedArticles = new HashMap<>();
    private ListItem head = null;
    private ListItem tail = null;

    public Person(int id, String name, int age) {
        this.id = id;
        this.name = name;
        this.age = age;
    }

    public boolean strictEquals(Person person) {
        return true;
    }

    public int getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public HashMap<Integer, Integer> getValues() {
        return value;
    }

    public int getAge() {
        return age;
    }

    public List<Integer> getReceivedArticles() {
        ArrayList<Integer> articles = new ArrayList<>();
        ListItem current = head;
        while (current != null) {
            articles.add((Integer) current.getValue());
            current = current.next();
        }
        return articles;
    }

    public List<Integer> queryReceivedArticles() {
        List<Integer> result = new ArrayList<>();
        ListItem current = head;
        for (int i = 0; i < min(receivedArticles.size(), 5); i++) {
            if (current == null) {
                break;
            }
            result.add((Integer) current.getValue());
            current = current.next();
        }
        return result;
    }

    public void receiveArticle(int id) {
        ListItem newItem = new ListItem(id);
        if (head == null) {
            head = newItem;
            tail = newItem;
        } else {
            head.insertBefore(newItem);
            head = newItem;
        }
        if (receivedArticles.containsKey(id)) {
            receivedArticles.get(id).add(newItem);
        } else {
            ArrayList<ListItem> newList = new ArrayList<>();
            newList.add(newItem);
            receivedArticles.put(id, newList);
        }
    }

    public boolean containsTag(int id) {
        return tags.containsKey(id);
    }

    public TagInterface getTag(int id) {
        if (tags.containsKey(id)) {
            return tags.get(id);
        }
        return null;
    }

    public void addTag(TagInterface tag) {
        tags.put(tag.getId(), tag);
    }

    public boolean equals(Object object) {
        if (!(object instanceof Person)) {
            return false;
        }
        Person person = (Person) object;
        return person.getId() == id;
    }

    public boolean isLinked(PersonInterface person) {
        if (acquaintance.containsKey(person.getId())) {
            return true;
        }
        return this.id == person.getId();
    }

    public void link(PersonInterface person, int val) {
        acquaintance.put(person.getId(), person);
        value.put(person.getId(), val);
        if (val > bestAcquaintanceValue ||
            (val == bestAcquaintanceValue && person.getId() < bestAcquaintanceId)) {
            bestAcquaintanceValue = val;
            bestAcquaintanceId = person.getId();
        }
    }

    public void update(PersonInterface person, int val) {
        bestAcquaintanceId = -1;
        bestAcquaintanceValue = -10000;
        for (Integer id: value.keySet()) {
            Integer tempValue = value.get(id);
            if (tempValue > bestAcquaintanceValue
                || (tempValue == bestAcquaintanceValue && id < bestAcquaintanceId)) {
                bestAcquaintanceValue = tempValue;
                bestAcquaintanceId = id;
            }
        }
    }

    public void modify(PersonInterface person, int val) {
        int newVal = value.get(person.getId()) + val;
        if (newVal > 0) {
            value.put(person.getId(), newVal);
            if (newVal > bestAcquaintanceValue ||
                (newVal == bestAcquaintanceValue && person.getId() < bestAcquaintanceId)) {
                bestAcquaintanceValue = newVal;
                bestAcquaintanceId = person.getId();
            }
            if (val < 0) {
                if (person.getId() == bestAcquaintanceId) {
                    update(person, val);
                }
            }
            return;
        }
        acquaintance.remove(person.getId());
        value.remove(person.getId());
        if (bestAcquaintanceId == person.getId()) {
            update(person, val);
        }

        for (TagInterface tag : tags.values()) {
            if (tag.hasPerson(person)) {
                tag.delPerson(person);
            }
        }
    }

    public void delTag(int id) {
        tags.remove(id);
    }

    public int queryValue(PersonInterface person) {
        if (value.containsKey(person.getId())) {
            return value.get(person.getId());
        }
        return 0;
    }

    public boolean dfs(int id, HashMap<Integer, Boolean> visited) {
        if (this.id == id) {
            return true;
        }
        if (visited.containsKey(this.id)) {
            return false;
        }
        visited.put(this.id, true);
        for (PersonInterface personInterface : acquaintance.values()) {
            Person person = (Person) personInterface;
            if (person.dfs(id, visited)) {
                return true;
            }
        }
        return false;
    }

    public int queryBestAcquaintance() throws AcquaintanceNotFoundException {
        int max = 0;
        int result = 0;
        if (acquaintance.isEmpty()) {
            throw new AcquaintanceNotFoundException(this.id);
        }
        return bestAcquaintanceId;
    }

    public HashMap<Integer, PersonInterface> getAcquaintance() {
        return acquaintance;
    }

    public void delArticle(Integer id) {
        if (!receivedArticles.containsKey(id)) {
            return;
        }
        ArrayList<ListItem> delList = receivedArticles.get(id);
        for (ListItem current : delList) {
            if (current == head) {
                head = current.next();
            }
            if (current == tail) {
                tail = current.prev();
            }
            current.remove();
        }
        receivedArticles.remove(id);
    }
}