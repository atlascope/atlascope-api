import io

from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone

from atlascope.core.models import Dataset, Pin


def to_saveable_image(pil_image):
    output_bytes = io.BytesIO()
    pil_image.save(output_bytes, format="PNG")
    output_file = InMemoryUploadedFile(
        output_bytes, None, 'file.png', 'image/png', output_bytes.getbuffer().nbytes, None
    )
    return output_file


def save_output_dataset(original_dataset, job_name, output_image, outputs_dict):
    outputs_dict['origin'] = f'Job Spawned at {timezone.now()}'
    new_dataset = Dataset(
        name=f'{original_dataset.name} {job_name}',
        description=f'{job_name} for {original_dataset.name} as of {timezone.now()}',
        public=original_dataset.public,
        metadata=outputs_dict,
        dataset_type='analytics',
        source_dataset=original_dataset,
    )
    new_dataset.content.save(
        f'{job_name.replace(" ", "_")}.png',
        to_saveable_image(output_image),
    )
    new_dataset.save()

    new_pin_location = [5, 5]
    # find an unoccupied space in the original dataset space
    existing_nearby_pin_locations = [list(x.location.tuple) for x in original_dataset.pins.all()]
    while new_pin_location in existing_nearby_pin_locations:
        new_pin_location[0] += 5
        if new_pin_location in existing_nearby_pin_locations:
            new_pin_location[1] += 5

    new_pin = Pin(
        parent_dataset=original_dataset,
        child_dataset=new_dataset,
        location=Point(new_pin_location),
        note=f'Generated by {job_name} job',
        color='black',
    )
    new_pin.save()
