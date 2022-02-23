from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
import factory

from atlascope.core import models


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class DatasetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Dataset

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    description = factory.Faker('sentence')
    public = factory.Faker('boolean')
    content = None
    metadata = {}
    dataset_type = 'tile_source'

    @factory.post_generation
    def source_dataset(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.source_dataset = extracted


class InvestigationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Investigation

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    description = factory.Faker('sentence')
    owner = factory.SubFactory(UserFactory)
    notes = factory.Faker('sentence')

    @factory.post_generation
    def datasets(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for dataset in extracted:
                self.datasets.add(dataset)


class PinFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Pin

    id = factory.Faker('uuid4')
    context = factory.SubFactory(InvestigationFactory)
    parent = factory.SubFactory(DatasetFactory)
    child = factory.SubFactory(DatasetFactory)
    child_location = Point(5, 5)
    color = 'red'
    note = factory.Faker('sentence')


class JobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Job

    id = factory.Faker('uuid4')
    context = factory.SubFactory(InvestigationFactory)
    original_dataset = factory.SubFactory(DatasetFactory)
    additional_inputs = {}
    job_type = 'average_color'

    @factory.post_generation
    def resulting_datasets(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for resulting_dataset in extracted:
                self.resulting_datasets.add(resulting_dataset)
