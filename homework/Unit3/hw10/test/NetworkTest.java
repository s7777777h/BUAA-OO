import com.oocourse.spec2.exceptions.*;

import static java.lang.Math.min;
import static org.junit.Assert.*;

import com.oocourse.spec2.main.PersonInterface;
import com.oocourse.spec2.main.NetworkInterface;
import org.junit.runner.RunWith;
import org.junit.Test;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.*;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Random;

@RunWith(Parameterized.class)
public class NetworkTest {

    private final Network network;
    private final Network clonedNetwork;
    private final ArrayList <Person> persons;
    private final ArrayList <Person> clonedPersons;

    public NetworkTest(Network network, ArrayList <Person> persons, Network clonedNetwork, ArrayList <Person> clonedPersons) {
        this.network = network;
        this.persons = persons;
        this.clonedNetwork = clonedNetwork;
        this.clonedPersons = clonedPersons;
    }

    private PersonInterface p(int id, String name) {
        return new Person(id, name, 20);
    }

    @Parameters
    public static Collection prepareData() {
        long seed = System.currentTimeMillis();
        Random random = new Random(seed);
        int testNum = 300;
        Object[][] object = new Object[testNum][];
        int maxPerson = 50;
        for (int i = 0; i < testNum; i++) {
            Network network = new Network();
            Network clonedNetwork = new Network();
            ArrayList<Person> persons = new ArrayList<>();
            ArrayList<Person> clonedPersons = new ArrayList<>();
            int numPersons = random.nextInt(maxPerson + 1);
            generatePersons(random, network, persons, numPersons, clonedNetwork, clonedPersons);
            int maxRelations = min(10 * numPersons, numPersons * (numPersons - 1) / 2);
            addRelations(random, network, persons, random.nextInt(maxRelations + 1), clonedNetwork, clonedPersons);
            modifyRelations(random, network, persons, clonedNetwork, clonedPersons);
            object[i] = new Object[]{network, persons, clonedNetwork, clonedPersons};
        }
        return Arrays.asList(object);
    }

    public static void generatePersons(Random random, Network network, ArrayList<Person> persons, int numPersons, Network clonedNetwork, ArrayList<Person> clonedPersons) {
        HashSet<Integer> personIds = new HashSet<>();
        HashSet<Integer> ages = new HashSet<>();
        for (int j = 0; j < numPersons; ++j) {
            int id = random.nextInt(Integer.MAX_VALUE);
            while (personIds.contains(id)) {
                id = random.nextInt(Integer.MAX_VALUE);
            }
            if (!personIds.contains(id)) {
                personIds.add(id);
                String name = "person" + id;
                int age = random.nextInt(200);
                while (ages.contains(age)) {
                    age = random.nextInt(200);
                }
                ages.add(age);
                Person person = new Person(id, name, age);
                persons.add(person);
                clonedPersons.add(new Person(id, name, age));
            }
        }
        for (Person person : persons) {
            try {
                network.addPerson(person);
            } catch (EqualPersonIdException e) {
                e.printStackTrace();
            }
        }
        for (Person person : clonedPersons) {
            try {
                clonedNetwork.addPerson(person);
            } catch (EqualPersonIdException e) {
                e.printStackTrace();
            }
        }
    }

    public static void addRelations(Random random, Network network, ArrayList<Person> persons, int numRelations, Network clonedNetwork, ArrayList<Person> clonedPersons) {
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
                int value = random.nextInt(100);
                network.addRelation(person1.getId(), person2.getId(), value);
                clonedNetwork.addRelation(person1.getId(), person2.getId(), value);
            } catch (PersonIdNotFoundException | EqualRelationException e) {
                e.printStackTrace();
            }
            ++count;
        }
    }

    public static void modifyRelations(Random random, Network network, ArrayList<Person> persons, Network clonedNetwork, ArrayList<Person> clonedPersons) {
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
                        int value = -random.nextInt(100);
                        network.modifyRelation(person.getId(), person1.getId(), value);
                        clonedNetwork.modifyRelation(person.getId(), person1.getId(), value);
                    } catch (PersonIdNotFoundException | EqualPersonIdException | RelationNotFoundException e) {
                        throw new RuntimeException(e);
                    }
                }
            }
        }
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

    @org.junit.Test
    public void queryCoupleSumTest() {
        emptyNetworkQueryCoupleSumTest();
        int sum = 0;
        PersonInterface oldPersons[] = clonedNetwork.getPersons();
        for (int i = 0; i < persons.size(); i++) {
            Person person1 = persons.get(i);
            for (int j = i + 1; j < persons.size(); j++) {
                Person person2 = persons.get(j);
                try {
                    if (network.queryBestAcquaintance(person1.getId()) == person2.getId()
                        && network.queryBestAcquaintance(person2.getId()) == person1.getId()) {
                        ++sum;
                    }
                } catch (AcquaintanceNotFoundException | PersonIdNotFoundException e) {

                }
            }
        }
        assertEquals(sum, network.queryCoupleSum());
        PersonInterface newPersons[] = network.getPersons();
        assertTrue(isPure(oldPersons, newPersons));
    }

    public void emptyNetworkQueryCoupleSumTest() {
        Network emptyNetwork = new Network();
        assertEquals(0, emptyNetwork.queryCoupleSum());
    }
}
