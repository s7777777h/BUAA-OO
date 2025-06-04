import com.oocourse.spec3.exceptions.*;

import static java.lang.Math.min;
import static org.junit.Assert.*;

import com.oocourse.spec3.main.MessageInterface;
import com.oocourse.spec3.main.PersonInterface;
import com.oocourse.spec3.main.NetworkInterface;
import com.oocourse.spec3.main.TagInterface;
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
    private final HashMap <Integer, Integer> emojis;
    private final HashMap <Integer, EmojiMessage> emojiMessageHashMap;

    public NetworkTest(Network network, ArrayList <Person> persons, Network clonedNetwork,
        ArrayList <Person> clonedPersons, HashMap<Integer, Integer> emojis, HashMap <Integer, EmojiMessage> emojiMessageHashMap) {
        this.network = network;
        this.persons = persons;
        this.clonedNetwork = clonedNetwork;
        this.clonedPersons = clonedPersons;
        this.emojis = emojis;
        this.emojiMessageHashMap = emojiMessageHashMap;
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
        int maxPerson = 10;
        for (int i = 0; i < testNum; i++) {
            Network network = new Network();
            Network clonedNetwork = new Network();
            ArrayList<Person> persons = new ArrayList<>();
            ArrayList<Person> clonedPersons = new ArrayList<>();
            HashMap <Integer, Integer> emojis = new HashMap<>();
            HashMap <Integer, EmojiMessage> emojiMessageHashMap = new HashMap<>();
            int numPersons = random.nextInt(maxPerson + 1);
            generatePersons(random, network, persons, numPersons, clonedNetwork, clonedPersons);
            int maxRelations = min(10 * numPersons, numPersons * (numPersons - 1) / 2);
            addRelations(random, network, persons, random.nextInt(maxRelations + 1), clonedNetwork, clonedPersons);
            modifyRelations(random, network, persons, clonedNetwork, clonedPersons);
            generateEmojis(random, network, persons, numPersons, clonedNetwork, clonedPersons, emojis, emojiMessageHashMap);
            object[i] = new Object[]{network, persons, clonedNetwork, clonedPersons, emojis,emojiMessageHashMap};
        }
        return Arrays.asList(object);
    }

    public static void generateEmojis(Random random, Network network, ArrayList<Person> persons, int numPersons, Network clonedNetwork, ArrayList<Person> clonedPersons, HashMap<Integer, Integer> emojis, HashMap <Integer, EmojiMessage> emojiMessageHashMap) {
        int messageIdCnt = 0;
        for (int j = 0; j < numPersons; ++j) {
            int id = random.nextInt(Integer.MAX_VALUE);
            while (emojis.containsKey(id)) {
                id = random.nextInt(Integer.MAX_VALUE);
            }
            if (!emojis.containsKey(id)) {
                emojis.put(id, 0);
                try {
                    network.storeEmojiId(id);
                } catch (EqualEmojiIdException e) {
                    throw new RuntimeException(e);
                }
            }
        }
        for (Integer emojiId: emojis.keySet()) {
            int loopTime = random.nextInt(20);
            for (int i = 0; i <= loopTime; ++i) {
                TagInterface tag = new Tag(messageIdCnt);
                EmojiMessage em = new EmojiMessage(messageIdCnt, emojiId,
                    persons.get(0), tag);
                emojis.put(emojiId, emojis.get(emojiId) + 1);
                try {
                    network.addTag(persons.get(0).getId(), tag);
                } catch (EqualTagIdException | PersonIdNotFoundException e) {
                    e.printStackTrace();
                }
                ++ messageIdCnt;
                try {
                    try{
                        network.addMessage(em);
                    } catch (EqualMessageIdException | EmojiIdNotFoundException | ArticleIdNotFoundException | EqualPersonIdException e) {
                        e.printStackTrace();
                    }
                    network.sendMessage(em.getId());
                } catch (MessageIdNotFoundException | TagIdNotFoundException | RelationNotFoundException e) {
                    e.printStackTrace();
                }
            }
            if (persons.size() > 2) {
                EmojiMessage em = new EmojiMessage(messageIdCnt, emojiId,
                        persons.get(0), persons.get(1));
                emojiMessageHashMap.put(emojiId, em);
                try{
                    network.addMessage(em);
                } catch (EqualMessageIdException | EmojiIdNotFoundException | ArticleIdNotFoundException | EqualPersonIdException e) {
                    e.printStackTrace();
                }

            }
            ++messageIdCnt;
        }
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

    @org.junit.Test
    public void deleteColdEmojiTest() {
        int minHeat = Integer.MAX_VALUE;
        int maxHeat = Integer.MIN_VALUE;
        for (Integer heat: emojis.values()) {
            if (heat < minHeat) {
                minHeat = heat;
            }
            if (heat > maxHeat) {
                maxHeat = heat;
            }
        }
        for (int i = minHeat; i <= maxHeat; ++i) {
            singleDeleteColdTest(i);
        }
    }

    public void singleDeleteColdTest(int heat) {
        System.out.println("----------------deleteColdEmojiTest: " + heat);
        System.out.print("Before emojiId: ");
        for (Integer emojiId: emojis.keySet()) {
            System.out.print(emojiId + " ");
        }
        System.out.println();
        System.out.print("Before emojiPopularity: ");
        for (Integer emojiId: emojis.keySet()) {
            System.out.print(emojis.get(emojiId) + " ");
        }
        System.out.println();
        ArrayList<Integer> delList = new ArrayList<>();
        for (Integer emojiId: emojis.keySet()) {
            if (emojis.get(emojiId) < heat) {
                delList.add(emojiId);
            }
        }
        System.out.print("delList: ");
        for (Integer emojiId: delList) {
            System.out.print(emojiId + " ");
        }
        System.out.println();
        System.out.print("delList popularity: ");
        for (Integer emojiId: delList) {
            System.out.print(emojis.get(emojiId) + " ");
        }
        System.out.println();
        for (Integer emojiId: delList) {
            emojis.remove(emojiId);
        }
        System.out.print("After emojiId: ");
        for (Integer emojiId: emojis.keySet()) {
            System.out.print(emojiId + " ");
        }
        System.out.println();
        System.out.print("After emojiPopularity: ");
        for (Integer emojiId: emojis.keySet()) {
            System.out.print(emojis.get(emojiId) + " ");
        }
        System.out.println();
        assertEquals(emojis.size(), network.deleteColdEmoji(heat));
        for (Integer emojiId: emojis.keySet()) {
            try {
                assertEquals(emojis.get(emojiId), (Integer) network.queryPopularity(emojiId));
            } catch (EmojiIdNotFoundException e) {
                fail("EmojiIdNotFoundException");
            }
        }
        for (Integer emojiId: delList) {
            if (emojiMessageHashMap.containsKey(emojiId)) {
                int messageId = emojiMessageHashMap.get(emojiId).getId();
                assertFalse(network.containsMessage(messageId));
            }
        }
    }
}
