import com.oocourse.spec1.exceptions.AcquaintanceNotFoundException;
import com.oocourse.spec1.main.PersonInterface;
import com.oocourse.spec1.main.TagInterface;
import java.util.HashMap;

public class Person implements PersonInterface {
    private final int id;
    private final String name;
    private final int age;
    private final HashMap<Integer, PersonInterface> acquaintance = new HashMap<>();
    private final HashMap<Integer, Integer> value = new HashMap<>();
    private final HashMap<Integer, TagInterface> tags = new HashMap<>();

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

    public int getAge() {
        return age;
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
    }

    public void modify(PersonInterface person, int val) {
        int newVal = value.get(person.getId()) + val;
        if (newVal > 0) {
            value.put(person.getId(), newVal);
            return;
        }
        acquaintance.remove(person.getId());
        value.remove(person.getId());
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
        for (PersonInterface person : acquaintance.values()) {
            if (value.get(person.getId()) > max) {
                max = value.get(person.getId());
                result = person.getId();
            }
            if (value.get(person.getId()) == max) {
                if (person.getId() < result) {
                    result = person.getId();
                }
            }
        }
        return result;
    }

    public HashMap<Integer, PersonInterface> getAcquaintance() {
        return acquaintance;
    }
}
