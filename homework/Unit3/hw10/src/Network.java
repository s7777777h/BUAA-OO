import com.oocourse.spec2.exceptions.AcquaintanceNotFoundException;
import com.oocourse.spec2.exceptions.ArticleIdNotFoundException;
import com.oocourse.spec2.exceptions.ContributePermissionDeniedException;
import com.oocourse.spec2.exceptions.DeleteArticlePermissionDeniedException;
import com.oocourse.spec2.exceptions.DeleteOfficialAccountPermissionDeniedException;
import com.oocourse.spec2.exceptions.EqualArticleIdException;
import com.oocourse.spec2.exceptions.EqualOfficialAccountIdException;
import com.oocourse.spec2.exceptions.EqualPersonIdException;
import com.oocourse.spec2.exceptions.EqualRelationException;
import com.oocourse.spec2.exceptions.EqualTagIdException;
import com.oocourse.spec2.exceptions.PathNotFoundException;
import com.oocourse.spec2.exceptions.PersonIdNotFoundException;
import com.oocourse.spec2.exceptions.RelationNotFoundException;
import com.oocourse.spec2.exceptions.TagIdNotFoundException;
import com.oocourse.spec2.exceptions.OfficialAccountIdNotFoundException;
import com.oocourse.spec2.main.NetworkInterface;
import com.oocourse.spec2.main.OfficialAccountInterface;
import com.oocourse.spec2.main.PersonInterface;
import com.oocourse.spec2.main.TagInterface;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Queue;

public class Network implements NetworkInterface {
    private final HashMap<Integer, PersonInterface> persons = new HashMap<>();
    private final HashMap<Integer, OfficialAccountInterface> accounts = new HashMap<>();
    private final HashSet<Integer> articles = new HashSet<>();
    private final HashMap<Integer, Integer> articleContributors = new HashMap<>();
    private final HashMap<Integer, TagInterface> tags = new HashMap<>();
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
        for (TagInterface tagInterface: tags.values()) {
            Tag tag = (Tag) tagInterface;
            if (tag.hasPerson(person1) && tag.hasPerson(person2)) {
                tag.modifyRelation(person1, person2, value);
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
        for (TagInterface tagInterface: tags.values()) {
            Tag tag = (Tag) tagInterface;
            if (tag.hasPerson(person1) && tag.hasPerson(person2)) {
                tag.modifyRelation(person1, person2, value);
            }
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
        tags.put(tag.getId(), tag);
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
        tags.remove(tagId);
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

    public int queryTagValueSum(int personId, int tagId)
        throws PersonIdNotFoundException, TagIdNotFoundException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (!getPerson(personId).containsTag(tagId)) {
            throw(new TagIdNotFoundException(tagId));
        }
        return getPerson(personId).getTag(tagId).getValueSum();
    }

    public int queryCoupleSum() {
        int sum = 0;
        for (PersonInterface personInterface1: persons.values()) {
            Person person1 = (Person) personInterface1;
            if (person1.getAcquaintance().isEmpty()) {
                continue;
            }
            int person1Best;
            try {
                person1Best = person1.queryBestAcquaintance();
            } catch (AcquaintanceNotFoundException e) {
                continue;
            }
            Person person2 = (Person) persons.get(person1Best);
            if (person2.getId() < person1.getId()) {
                continue;
            }
            if (person2.getAcquaintance().isEmpty()) {
                continue;
            }
            int person2Best;
            try {
                person2Best = person2.queryBestAcquaintance();
            } catch (AcquaintanceNotFoundException e) {
                continue;
            }
            if (person2Best == person1.getId()) {
                sum++;
            }
        }
        return sum;
    }

    public boolean containsAccount(int id) {
        return accounts.containsKey(id);
    }

    public void createOfficialAccount(int personId, int accountId, String name)
        throws PersonIdNotFoundException, EqualOfficialAccountIdException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (containsAccount(accountId)) {
            throw(new EqualOfficialAccountIdException(accountId));
        }
        accounts.put(accountId, new OfficialAccount(personId, accountId, name));
        accounts.get(accountId).addFollower(getPerson(personId));
    }

    public void deleteOfficialAccount(int personId, int accountId)
        throws PersonIdNotFoundException, OfficialAccountIdNotFoundException,
        DeleteOfficialAccountPermissionDeniedException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (!containsAccount(accountId)) {
            throw(new OfficialAccountIdNotFoundException(accountId));
        }
        if (accounts.get(accountId).getOwnerId() != personId) {
            throw(new DeleteOfficialAccountPermissionDeniedException(personId, accountId));
        }
        accounts.remove(accountId);
    }

    public boolean containsArticle(int articleId) {
        return articles.contains(articleId);
    }

    public void contributeArticle(int personId, int accountId, int articleId)
        throws PersonIdNotFoundException, OfficialAccountIdNotFoundException,
        EqualArticleIdException, ContributePermissionDeniedException {
        if (!containsPerson(personId)) {
            throw new PersonIdNotFoundException(personId);
        }
        if (!containsAccount(accountId)) {
            throw new OfficialAccountIdNotFoundException(accountId);
        }
        Person person = (Person) persons.get(personId);
        OfficialAccount account = (OfficialAccount) accounts.get(accountId);
        if (containsArticle(articleId)) {
            throw(new EqualArticleIdException(articleId));
        }
        if (!account.containsFollower(person)) {
            throw(new ContributePermissionDeniedException(personId, articleId));
        }
        if (account.containsArticle(articleId)) {
            return;
        }
        articles.add(articleId);
        articleContributors.put(articleId, personId);
        account.addArticle(person, articleId);
        for (PersonInterface personInterface: persons.values()) {
            Person person1 = (Person) personInterface;
            if (!account.containsFollower(person1)) {
                continue;
            }
            person1.receiveArticle(articleId);
        }
    }

    public void deleteArticle(int personId, int accountId, int articleId)
        throws PersonIdNotFoundException, OfficialAccountIdNotFoundException,
        ArticleIdNotFoundException, DeleteArticlePermissionDeniedException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        if (!containsAccount(accountId)) {
            throw(new OfficialAccountIdNotFoundException(accountId));
        }
        OfficialAccount account = (OfficialAccount) accounts.get(accountId);
        if (!account.containsArticle(articleId)) {
            throw(new ArticleIdNotFoundException(articleId));
        }
        if (account.getOwnerId() != personId) {
            throw(new DeleteArticlePermissionDeniedException(personId, articleId));
        }
        for (PersonInterface personInterface: persons.values()) {
            Person person1 = (Person) personInterface;
            if (account.containsFollower(person1)) {
                person1.delArticle(articleId);
            }
        }
        account.subContribution(articleId);
        account.removeArticle(articleId);
    }

    public void followOfficialAccount(int personId, int accountId)
        throws PersonIdNotFoundException,
        OfficialAccountIdNotFoundException, EqualPersonIdException {
        if (!containsPerson(personId)) {
            throw new PersonIdNotFoundException(personId);
        }
        if (!containsAccount(accountId)) {
            throw new OfficialAccountIdNotFoundException(accountId);
        }
        OfficialAccount account = (OfficialAccount) accounts.get(accountId);
        Person person = (Person) persons.get(personId);
        if (account.containsFollower(person)) {
            throw new EqualPersonIdException(personId);
        }
        account.addFollower(person);
    }

    public int queryBestContributor(int accountId)
        throws OfficialAccountIdNotFoundException {
        if (!containsAccount(accountId)) {
            throw(new OfficialAccountIdNotFoundException(accountId));
        }
        return accounts.get(accountId).getBestContributor();
    }

    public List<Integer> queryReceivedArticles(int personId)
        throws PersonIdNotFoundException {
        if (!containsPerson(personId)) {
            throw(new PersonIdNotFoundException(personId));
        }
        return new ArrayList<>(getPerson(personId).queryReceivedArticles());
    }

    public int queryShortestPath(int personId1, int personId2)
        throws PersonIdNotFoundException, PathNotFoundException {
        if (!containsPerson(personId1)) {
            throw new PersonIdNotFoundException(personId1);
        }
        if (!containsPerson(personId2)) {
            throw new PersonIdNotFoundException(personId2);
        }
        Person person1 = (Person) persons.get(personId1);
        Person person2 = (Person) persons.get(personId2);
        HashMap<Integer, Boolean> visited = new HashMap<>();
        Queue<Integer> queue = new java.util.LinkedList<>();
        Queue<Integer> dis = new java.util.LinkedList<>();
        queue.offer(personId1);
        dis.offer(0);
        for (PersonInterface personInterface: persons.values()) {
            visited.put(personInterface.getId(), false);
        }
        visited.put(personId1, true);
        while (!queue.isEmpty()) {
            int u = queue.poll();
            int d = dis.poll();
            if (u == personId2) {
                return d;
            }
            Person person = (Person) persons.get(u);
            HashMap<Integer, PersonInterface> acquaintance = person.getAcquaintance();
            for (PersonInterface personInterface: acquaintance.values()) {
                Person v = (Person) personInterface;
                if (visited.get(v.getId())) {
                    continue;
                }
                queue.offer(v.getId());
                dis.offer(d + 1);
                visited.put(v.getId(), true);
            }
        }
        throw new PathNotFoundException(personId1, personId2);
    }

}
