# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-12-03 19:13
from __future__ import unicode_literals

from django.db import migrations, models


RESULT_FIELDS = [
    'guid', 'created_date', 'last_modified_date', 'result_data', 'we_contacted', 'host_contacted', 'deemed_irrelevant',
    'flag_for_analysis', 'comments', 'match_removed', 'created_by_id', 'last_modified_by_id',
]
CONTACT_NOTE_FIELDS = ['guid', 'created_date', 'last_modified_date', 'institution', 'comments', 'created_by_id']

# For a few individuals that have duplicate IDs across project, the same id got used twice for mathmaker.
# This was actually a bug, as matchmaker replaces when it recieves a duplicate ID
DUPLICATED_SUBMISSION_IDS = {
    '89dcbe5e752737cb1991dd34dfae68c1',
     'BON_UC499_1_1',
     'WAL_CH2900_CH2901',
     'WAL_CH5200_CH5201',
     'WAL_CH5700_CH5701',
     'WAL_DC2200_DC2201',
     'WAL_DC3500_DC3501',
     'WAL_LIS4900_LIS4901',
     'WAL_PAC2800_PAC2801',
}


def bulk_copy_models(db_alias, source_model, dest_model, fields, field_process_funcs={}, db_filter=None):
    all_source_models = source_model.objects.using(db_alias)
    if db_filter:
        all_source_models = all_source_models.filter(db_filter)
    all_source_models = all_source_models.all()
    if all_source_models:
        print('Copying {} {} to {}'.format(all_source_models.count(), source_model.__name__, dest_model.__name__))
        try:
            new_models = [
                dest_model(**{field: field_process_funcs.get(field, getattr)(model, field) for field in fields})
                for model in all_source_models
            ]
        except Exception as e:
            import pdb; pdb.set_trace()
        dest_model.objects.bulk_create(new_models)


def migrate_submissions(apps, schema_editor):
    Individual = apps.get_model("seqr", "Individual")
    MatchmakerSubmission = apps.get_model("matchmaker", "MatchmakerSubmission")
    db_alias = schema_editor.connection.alias

    fields = [
        'guid', 'created_date', 'last_modified_date', 'submission_id', 'label', 'contact_name', 'contact_href', 'features',
        'genomicFeatures', 'deleted_date', 'created_by_id', 'deleted_by_id', 'individual_id'
    ]
    found_duplicates = set()

    def get_submitted_data_field(model, field):
        value = model.mme_submitted_data['patient']
        for field_key in field.split('_'):
            value = value[field_key]
        return value

    def get_submission_id(model, field):
        submission_id = get_submitted_data_field(model, 'id')
        if submission_id in DUPLICATED_SUBMISSION_IDS:
            if submission_id in found_duplicates:
                submission_id = '{}_b'.format(submission_id)
            else:
                found_duplicates.add(submission_id)
        return submission_id

    field_process_funcs = {
        'guid': lambda model, field: model.guid.replace('I', 'MS')[:30],
        'created_date': lambda model, field: model.mme_submitted_date,
        'deleted_date': lambda model, field: model.mme_deleted_date,
        'last_modified_date': lambda model, field: model.mme_deleted_date or model.mme_submitted_date,
        'deleted_by_id': lambda model, field: model.mme_deleted_by_id,
        'individual_id': lambda model, field: model.id,
        'submission_id': get_submission_id,
        'label': get_submitted_data_field,
        'contact_name': get_submitted_data_field,
        'contact_href': get_submitted_data_field,
        'features': get_submitted_data_field,
        'genomicFeatures': get_submitted_data_field,
    }

    bulk_copy_models(
        db_alias, Individual, MatchmakerSubmission, fields, field_process_funcs=field_process_funcs,
        db_filter=models.Q(mme_submitted_data__isnull=False),
    )


def copy_results(apps, schema_editor):
    SeqrResult = apps.get_model("seqr", "MatchmakerResult")
    MatchmakerResult = apps.get_model("matchmaker", "MatchmakerResult")
    db_alias = schema_editor.connection.alias

    field_process_funcs = {'submission': lambda model, field: model.individual.matchmakersubmission}
    fields = RESULT_FIELDS + field_process_funcs.keys()
    bulk_copy_models(db_alias, SeqrResult, MatchmakerResult, fields, field_process_funcs=field_process_funcs)


def copy_contact_notes(apps, schema_editor):
    SeqrContactNotes = apps.get_model("seqr", "MatchmakerContactNotes")
    MatchmakerContactNotes = apps.get_model("matchmaker", "MatchmakerContactNotes")
    db_alias = schema_editor.connection.alias

    bulk_copy_models(db_alias, SeqrContactNotes, MatchmakerContactNotes, CONTACT_NOTE_FIELDS)


def reverse_migrate_submissions(apps, schema_editor):
    MatchmakerSubmission = apps.get_model("matchmaker", "MatchmakerSubmission")
    db_alias = schema_editor.connection.alias

    for submission in MatchmakerSubmission.objects.using(db_alias).all().prefetch_related('individual'):
        ind = submission.individual
        ind.mme_deleted_by_id = submission.deleted_by_id
        ind.mme_deleted_date = submission.deleted_date
        ind.mme_submitted_date = submission.created_date
        ind.mme_submitted_data = submission.get_json_for_external_match()
        ind.save()


def reverse_copy_results(apps, schema_editor):
    SeqrResult = apps.get_model("seqr", "MatchmakerContactNotes")
    MatchmakerResult = apps.get_model("matchmaker", "MatchmakerResult")
    db_alias = schema_editor.connection.alias

    field_process_funcs = {'individual_id': lambda model, field: model.matchmakersubmission.individual_id}
    fields = RESULT_FIELDS + field_process_funcs.keys()
    bulk_copy_models(db_alias, MatchmakerResult, SeqrResult, fields, field_process_funcs=field_process_funcs)


def reverese_copy_contact_notes(apps, schema_editor):
    SeqrContactNotes = apps.get_model("seqr", "MatchmakerContactNotes")
    MatchmakerContactNotes = apps.get_model("matchmaker", "MatchmakerContactNotes")
    db_alias = schema_editor.connection.alias

    bulk_copy_models(db_alias, MatchmakerContactNotes, SeqrContactNotes, CONTACT_NOTE_FIELDS)


class Migration(migrations.Migration):

    dependencies = [
        ('seqr', '0001_squashed_0067_remove_project_custom_reference_populations'),
        ('matchmaker', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_submissions, reverse_code=reverse_migrate_submissions),
        migrations.RunPython(copy_results, reverse_code=reverse_copy_results),
        migrations.RunPython(copy_contact_notes, reverse_code=reverese_copy_contact_notes),

        migrations.RemoveField(
            model_name='matchmakercontactnotes',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='matchmakerresult',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='matchmakerresult',
            name='individual',
        ),
        migrations.RemoveField(
            model_name='matchmakerresult',
            name='last_modified_by',
        ),
        migrations.RemoveField(
            model_name='individual',
            name='mme_deleted_by',
        ),
        migrations.RemoveField(
            model_name='individual',
            name='mme_deleted_date',
        ),
        migrations.RemoveField(
            model_name='individual',
            name='mme_id',
        ),
        migrations.RemoveField(
            model_name='individual',
            name='mme_submitted_data',
        ),
        migrations.RemoveField(
            model_name='individual',
            name='mme_submitted_date',
        ),
        migrations.DeleteModel(
            name='MatchmakerContactNotes',
        ),
        migrations.DeleteModel(
            name='MatchmakerResult',
        ),
    ]