import com.oocourse.spec1.exceptions.EqualPersonIdException;
import com.oocourse.spec1.exceptions.EqualRelationException;
import com.oocourse.spec1.exceptions.PersonIdNotFoundException;

import static java.lang.Math.min;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.oocourse.spec1.exceptions.RelationNotFoundException;
import com.oocourse.spec1.main.PersonInterface;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.*;

import java.util.*;

@RunWith(Parameterized.class)
public class Test {

    private final Network network;
    private final ArrayList <Person> persons;

    public Test(Network network, ArrayList <Person> persons) {
        this.network = network;
        this.persons = persons;
    }

    @Parameters
    public static Collection prepareData() {
        long seed = System.currentTimeMillis();
        Random random = new Random(seed);
        int testNum = 50;
        Object[][] object = new Object[testNum][];
        int maxPerson = 50;
        for (int i = 0; i < testNum; i++) {
            Network network = new Network();
            ArrayList<Person> persons = new ArrayList<>();
            int numPersons = random.nextInt(maxPerson + 1);
            generatePersons(random, network, persons, numPersons);
            int maxRelations = min(10 * numPersons, numPersons * (numPersons - 1) / 2);
            addRelations(random, network, persons, random.nextInt(maxRelations + 1));
            modifyRelations(random, network, persons);
            object[i] = new Object[]{network, persons};
        }
        return Arrays.asList(object);
    }

    public static void generatePersons(Random random, Network network, ArrayList<Person> persons, int numPersons) {
        HashSet<Integer> personIds = new HashSet<>();
        for (int j = 0; j < numPersons; ++j) {
            int id = random.nextInt(Integer.MAX_VALUE);
            while (personIds.contains(id)) {
                id = random.nextInt(Integer.MAX_VALUE);
            }
            if (!personIds.contains(id)) {
                personIds.add(id);
                String name = "person" + id;
                int age = random.nextInt(200);
                Person person = new Person(id, name, age);
                persons.add(person);
            }
        }
        for (Person person : persons) {
            try {
                network.addPerson(person);
            } catch (EqualPersonIdException e) {
                e.printStackTrace();
            }
        }
    }

    public static void addRelations(Random random, Network network, ArrayList<Person> persons, int numRelations) {
        HashSet<String> added = new HashSet<>();
        int count = 0;
        while(count < numRelations) {
            int index1 = random.nextInt(persons.size());
            int index2 = random.nextInt(persons.size());
            while(index1 == index2) {
                index2 = random.nextInt(persons.size());
            }
            Person person1 = persons.get(index1);
            Person person2 = persons.get(index2);
            int p1 = person1.getId();
            int p2 = person2.getId();
            int minId = min(p1, p2);
            int maxId = Math.max(p1, p2);
            String key = minId + "-" + maxId;
            if(added.contains(key)) {
                continue;
            }
            added.add(key);
            try {
                network.addRelation(person1.getId(), person2.getId(), random.nextInt(100));
            } catch (PersonIdNotFoundException | EqualRelationException e) {
                e.printStackTrace();
            }
            ++count;
        }
    }

    public static void modifyRelations(Random random, Network network, ArrayList<Person> persons) {
        for (Person person: persons) {
            HashMap<Integer, PersonInterface> acquaintance = person.getAcquaintance();
            ArrayList <PersonInterface> personList = new ArrayList<>(acquaintance.values());
            for (PersonInterface personInterface: personList) {
                Person person1 = (Person) personInterface;
                if (person1.getId() >= person.getId()) {
                    continue;
                }
                if (random.nextInt(10) == 0) {
                    try {
                        network.modifyRelation(person.getId(), person1.getId(), -random.nextInt(100));
                    } catch (PersonIdNotFoundException | EqualPersonIdException | RelationNotFoundException e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
    }

    @org.junit.Test
    public void queryTripleSumTest() {
        int sum = 0;
        PersonInterface oldPersons[] = network.getPersons();
        for (int i = 0; i < persons.size(); i++) {
            Person person1 = persons.get(i);
            for (int j = i + 1; j < persons.size(); j++) {
                Person person2 = persons.get(j);
                for (int k = j + 1; k < persons.size(); k++) {
                    Person person3 = persons.get(k);
                    if (person1.isLinked(person2) && person2.isLinked(person3) && person3.isLinked(person1)) {
                        ++sum;
                    }
                }
            }
        }
        assertEquals(sum, network.queryTripleSum());
        PersonInterface newPersons[] = network.getPersons();
        assertTrue(isPure(oldPersons, newPersons));
    }

    private boolean isPure(PersonInterface persons1[], PersonInterface persons2[]) {
        if (persons1.length != persons2.length) {
            return false;
        }
        for (int i = 0;i < persons1.length; ++i) {
            boolean flag = false;
            for (int j = 0;j < persons2.length; ++j) {
                Person person1 = (Person) persons1[i];
                Person person2 = (Person) persons2[j];
                if (person1.strictEquals(person2)) {
                    flag = true;
                    break;
                }
            }
            if (!flag) {
                return false;
            }
        }
        return true;
    }
}