import com.oocourse.spec1.exceptions.AcquaintanceNotFoundException;
import com.oocourse.spec1.exceptions.EqualPersonIdException;
import com.oocourse.spec1.exceptions.EqualRelationException;
import com.oocourse.spec1.exceptions.EqualTagIdException;
import com.oocourse.spec1.exceptions.PersonIdNotFoundException;
import com.oocourse.spec1.exceptions.RelationNotFoundException;
import com.oocourse.spec1.exceptions.TagIdNotFoundException;
import com.oocourse.spec1.main.NetworkInterface;
import com.oocourse.spec1.main.PersonInterface;
import com.oocourse.spec1.main.TagInterface;

import java.util.HashMap;

public class Network implements NetworkInterface {
    private final HashMap<Integer, PersonInterface> persons = new HashMap<>();
    private int tripleSum = 0;

    public PersonInterface[] getPersons() {
        return persons.values().toArray(new PersonInterface[0]);
    }

    public boolean containsPerson(int id) {
        return persons.containsKey(id);
    }

    public PersonInterface getPerson(int id) {
        if (containsPerson(id)) {
            return persons.get(id);
        }
        return null;
    }

    public void addPerson(PersonInterface person) throws EqualPersonIdException {
        if (containsPerson(person.getId())) {
            throw(new EqualPersonIdException(person.getId()));
        }
        persons.put(person.getId(), person);
    }

    @Override
    public void addRelation(int id1, int id2, int value)
        throws PersonIdNotFoundException, EqualRelationException {
        if (!containsPerson(id1) || !containsPerson(id2)) {
            if (!containsPerson(id1)) {
                throw(new PersonIdNotFoundException(id1));
            }
            if (!containsPerson(id2)) {
                throw(new PersonIdNotFoundException(id2));
            }
        }
        Person person1 = (Person) getPerson(id1);
        Person person2 = (Person) getPerson(id2);
        if (person1.isLinked(person2)) {
            throw(new EqualRelationException(id1, id2));
        }
        person1.link(person2, value);
        person2.link(person1, value);
        for (PersonInterface personInterface: person2.getAcquaintance().values()) {
            Person person = (Person) personInterface;
            if (person.getId() == person1.getId()) {
                continue;
            }
            if (person.isLinked(person1)) {
                tripleSum++;
            }
        }
    }

    @Override
    public void modifyRelation(int id1, int id2, int value)
        throws PersonIdNotFoundException, EqualPersonIdException, RelationNotFoundException {
        if (!containsPerson(id1) || !containsPerson(id2)) {
            if (!containsPerson(id1)) {
                throw(new PersonIdNotFoundException(id1));
            }
            if (!containsPerson(id2)) {
                throw(new PersonIdNotFoundException(id2));
            }
        }
        if (id1 == id2) {
            throw(new EqualPersonIdException(id1));
        }
        Person person1 = (Person) getPerson(id1);
        Person person2 = (Person) getPerson(id2);
        if (!person1.isLinked(person2)) {
            throw(new RelationNotFoundException(id1, id2));
        }
        boolean delRelation = queryValue(id1, id2) + value <= 0;
        person1.modify(person2, value);
        person2.modify(person1, value);
        if (!delRelation) {
            return;
        }
        for (PersonInterface personInterface: person2.getAcquaintance().values()) {
            Person person = (Person) personInterface;
            if (person.getId() == person1.getId()) {
                continue;
            }
            if (person.isLinked(person1)) {
                tripleSum--;
            }
        }
    }

    @Override
    public int queryValue(int id1, int id2)
        throws PersonIdNotFoundException, RelationNotFoundException {
        if (!containsPerson(id1)) {
            throw(new PersonIdNotFoundException(id1));
        }
        if (!containsPerson(id2)) {
            throw(new PersonIdNotFoundException(id2));
        }
        Person person1 = (Person) getPerson(id1);
        Person person2 = (Person) getPerson(id2);
        if (!person1.isLinked(person2)) {
            throw(new RelationNotFoundException(id1, id2));
        }
        return person1.queryValue(person2);
    }

    @Override
    public boolean isCircle(int id1, int id2) throws PersonIdNotFoundException {
        HashMap<Integer, Boolean> vis = new HashMap<>();
        if (!containsPerson(id1)) {
            throw(new PersonIdNotFoundException(id1));
        }
        if (!containsPerson(id2)) {
            throw(new PersonIdNotFoundException(id2));
        }
        Person person1 = (Person) getPerson(id1);
        boolean result = person1.dfs(id2, vis);
        return result;
    }

    @Override
    public int queryTripleSum() {
        return tripleSum;
    }

    @Override
    public void addTag(int personId, TagInterface tag)
        throws PersonIdNotFoundException, EqualTagIdException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (getPerson(personId).containsTag(tag.getId())) {
            throw(new EqualTagIdException(tag.getId()));
        }
        Person person = (Person) getPerson(personId);
        person.addTag(tag);
    }

    public void addPersonToTag(int personId1, int personId2, int tagId)
        throws PersonIdNotFoundException, RelationNotFoundException,
        TagIdNotFoundException, EqualPersonIdException {
        if (!containsPerson(personId1)) {
            throw(new PersonIdNotFoundException(personId1));
        }
        if (!containsPerson(personId2)) {
            throw(new PersonIdNotFoundException(personId2));
        }
        if (personId1 == personId2) {
            throw(new EqualPersonIdException(personId1));
        }
        Person person1 = (Person) getPerson(personId1);
        Person person2 = (Person) getPerson(personId2);
        if (!person2.isLinked(person1)) {
            throw(new RelationNotFoundException(personId1, personId2));
        }
        if (!person2.containsTag(tagId)) {
            throw(new TagIdNotFoundException(tagId));
        }
        TagInterface tag = person2.getTag(tagId);
        if (tag.hasPerson(person1)) {
            throw(new EqualPersonIdException(personId1));
        }
        if (tag.getSize() > 999) {
            return;
        }
        tag.addPerson(person1);
    }

    @Override
    public int queryTagAgeVar(int personId, int tagId)
        throws PersonIdNotFoundException, TagIdNotFoundException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (!getPerson(personId).containsTag(tagId)) {
            throw(new TagIdNotFoundException(tagId));
        }
        Person person = (Person) getPerson(personId);
        TagInterface tag = person.getTag(tagId);
        return tag.getAgeVar();
    }

    @Override
    public void delPersonFromTag(int personId1, int personId2, int tagId)
        throws PersonIdNotFoundException, TagIdNotFoundException {
        if (!containsPerson(personId1)) {
            throw(new PersonIdNotFoundException(personId1));
        }
        if (!containsPerson(personId2)) {
            throw(new PersonIdNotFoundException(personId2));
        }
        Person person1 = (Person) getPerson(personId1);
        Person person2 = (Person) getPerson(personId2);
        if (!person2.containsTag(tagId)) {
            throw(new TagIdNotFoundException(tagId));
        }
        TagInterface tag = person2.getTag(tagId);
        if (!tag.hasPerson(person1)) {
            throw(new PersonIdNotFoundException(personId1));
        }
        tag.delPerson(person1);
    }

    @Override
    public void delTag(int personId, int tagId)
        throws PersonIdNotFoundException, TagIdNotFoundException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (!getPerson(personId).containsTag(tagId)) {
            throw(new TagIdNotFoundException(tagId));
        }
        Person person = (Person) getPerson(personId);
        person.delTag(tagId);
    }

    @Override
    public int queryBestAcquaintance(int id)
        throws PersonIdNotFoundException, AcquaintanceNotFoundException {
        if (!containsPerson(id)) {
            throw(new PersonIdNotFoundException(id));
        }
        Person person = (Person) getPerson(id);
        return person.queryBestAcquaintance();
    }
}
