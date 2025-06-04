import com.oocourse.spec1.main.PersonInterface;
import com.oocourse.spec1.main.TagInterface;
import java.util.HashMap;

public class Tag implements TagInterface {
    private final int id;
    private final HashMap<Integer, PersonInterface> persons = new HashMap<>();

    public Tag(int id) {
        this.id = id;
    }

    public int getId() {
        return id;
    }

    public boolean equals(Object object) {
        if (!(object instanceof Tag)) {
            return false;
        }
        Tag tag = (Tag) object;
        return id == tag.getId();
    }

    public void addPerson(PersonInterface person) {
        persons.put(person.getId(), person);
    }

    public boolean hasPerson(PersonInterface person) {
        return persons.containsKey(person.getId());
    }

    public int getAgeMean() {
        if (persons.isEmpty()) {
            return 0;
        }
        int sum = 0;
        for (PersonInterface person : persons.values()) {
            sum += person.getAge();
        }
        return sum / persons.size();
    }

    public int getAgeVar() {
        if (persons.isEmpty()) {
            return 0;
        }
        int sum = 0;
        int mean = getAgeMean();
        for (PersonInterface person : persons.values()) {
            sum += (person.getAge() - mean) * (person.getAge() - mean);
        }
        return sum / persons.size();
    }

    public void delPerson(PersonInterface person) {
        persons.remove(person.getId());
    }

    public int getSize() {
        return persons.size();
    }
}
