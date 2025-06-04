import com.oocourse.spec3.main.PersonInterface;
import com.oocourse.spec3.main.TagInterface;
import java.util.HashMap;

public class Tag implements TagInterface {
    private final int id;
    private final HashMap<Integer, PersonInterface> persons = new HashMap<>();
    private int valueSum = 0;

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
        for (PersonInterface otherPerson : persons.values()) {
            if (otherPerson.isLinked(person)) {
                valueSum += 2 * person.queryValue(otherPerson);
            }
        }
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
        for (PersonInterface otherPerson : persons.values()) {
            if (otherPerson.isLinked(person)) {
                valueSum -= 2 * person.queryValue(otherPerson);
            }
        }
        persons.remove(person.getId());
    }

    public int getSize() {
        return persons.size();
    }

    public int getValueSum() {
        return valueSum;
    }

    public void modifyRelation(PersonInterface person1, PersonInterface person2,int value) {
        if (persons.containsKey(person1.getId()) && persons.containsKey(person2.getId())) {
            int oldValue = person1.queryValue(person2);
            if (oldValue + value > 0) {
                valueSum += 2 * value;
            }
            else {
                valueSum -= 2 * oldValue;
            }
        }
    }

    public HashMap<Integer, PersonInterface> getPersons() {
        return persons;
    }
}
