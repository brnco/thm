'''
handles airtable calls
'''
from pprint import pprint
import re
import ast
import time
import json
import pathlib
import logging
import requests
from datetime import timedelta, datetime
from pprint import pformat
from pyairtable import Api, Base, Table
from pyairtable.orm import Model, fields
from pyairtable.formulas import match
from pyairtable.api import types as pyairtable_types
from typing import Self, Any


RecordDict = pyairtable_types.RecordDict

logger = logging.getLogger('main_logger')


def config() -> dict:
    '''
    creates/ returns config object for Airtable setup
    airtable_config.json located in same dir as this script
    '''
    this_dirpath = pathlib.Path(__file__).parent.absolute()
    with open(this_dirpath / 'airtable_config.json', 'r') as config_file:
        atbl_config = json.load(config_file)
        pprint(atbl_config)
    return atbl_config


def get_api_key() -> str:
    '''
    returns the airtable API key from the config file
    '''
    atbl_config = config()
    return atbl_config['main']['api_key']


def get_field_map(obj_type: str) -> str:
    '''
    returns dictionary of field mappings for attr <-> Airtable <-> XLSX
    for specified object type, e.g. PhysicalAssetRecord
    '''
    module_dirpath = pathlib.Path(__file__).parent.parent.parent.absolute()
    field_map_filepath = 'field_mappings.json'
    with open(field_map_filepath, 'r') as field_map_file:
        field_mapping = json.load(field_map_file)
    return field_mapping[obj_type]


class THMAirtableRecord:
    '''
    super class for the various AirtableRecord() classes we'll create later
    defines a few methods we'll use for all Airtable records
    notably, send() and from_filemaker()
    '''
    primary_field = None

    def _fix_problem_attrs(self, attr_name: str, value: str) -> Any:
        '''
        for some of these we need an extra layer of formatting
        '''
        if attr_name == "filesize":
            value = int(value)
        return value

    @classmethod
    def from_filemaker(cls, row: dict, field_map: dict) -> Self:
        '''
        creates an Airtable record from a row of FileMaker data
        '''
        instance = cls()
        problem_attrs = ['filesize']
        for attr_name, mapping in field_map.items():
            try:
                assert mapping['fm']
            except KeyError:
                continue
            if not mapping['atbl']:
                continue
            try:
                column = mapping['fm']['column']
            except TypeError:
                column = mapping['fm']
            except Exception as exc:
                raise RuntimeError
            value = row[column]
            if not value:
                continue
            if attr_name in problem_attrs:
                value = instance._fix_problem_attrs(attr_name, value)
            '''
            if attr_name in link_field_attrs:
                value = instance._set_link_field(attr_name, value)
            '''
            try:
                setattr(instance, attr_name, value)
            except TypeError as exc:
                logger.error(f"attr_name: {attr_name}")
                logger.error(f"type(attr_name): {type(attr_name)}")
                logger.error(f"value: {value}")
                logger.error(f"type(value): {type(value)}")
                logger.error(exc, stack_info=True)
                raise RuntimeError("there was a problem parsing the above value to an Airtable field")
        return instance

    def _get_primary_key_info(self) -> tuple[str, str]:
        '''
        for send()
        gets primary key name and value
        '''
        atbl_tbl = self.meta.table
        # atbl_tbl_schema = Base.table(atbl_tbl.name).schema
        atbl_tbl_schema = atbl_tbl.schema()
        # atbl_tbl_schema = atbl_mtd.get_table_schema(atbl_tbl)
        primary_field_id = atbl_tbl_schema.primary_field_id
        for field in atbl_tbl_schema.fields:
            if field.id == primary_field_id:
                primary_field_name = field.name
                break
        try:
            self_primary_field_value = self._fields[primary_field_name]
        except KeyError:
            logger.warning(f"no value for primary field {primary_field_name} in record")
            logger.warning(f"using THMAirtableRecord() attribute instead = {self.primary_field}")
            self_primary_field_value = self.primary_field
        return primary_field_name, self_primary_field_value

    def _search_on_primary_field(self, primary_field_name: str,
                                 self_primary_field_value: str) -> RecordDict:
        '''
        searches for self_primary_field_value in primary_field_name
        '''
        atbl_tbl = self.meta.table
        logger.debug(f"searching table {atbl_tbl.name}")
        logger.debug(f"in field {primary_field_name}")
        logger.debug(f"for value {self_primary_field_value}")
        response = atbl_tbl.all(formula=match({primary_field_name: self_primary_field_value}))
        if len(response) > 1:
            logger.error(f"too many results for {self_primary_field_value} in field {primary_field_name}")
            raise ValueError("duplicate records in table")
        elif len(response) > 0:
            logger.debug("result found, updating Airtable record with local values...")
            atbl_rec_remote = self.from_id(response[0]['id'])
        else:
            logger.debug("no results found")
            return None
        return atbl_rec_remote

    def _fill_remote_rec_from_local(self, atbl_rec_remote: RecordDict) -> RecordDict:
        '''
        ugh we can't just assign a record id to an unsaved record
        and have that overwrite a remote record
        so instead we do this,
        where we take the remote record and fill it with local values
        '''
        for field, value in self._fields.items():
            try:
                atbl_rec_remote._fields[field] = value
            except (KeyError, TypeError) as exc:
                logger.exception(exc, stack_info=True)
                continue
        return atbl_rec_remote

    def _save_rec(self, atbl_rec: Self) -> Self:
        '''
        actually save the dang record
        '''
        try:
            atbl_rec.save()
            time.sleep(0.1)
            if atbl_rec.exists():
                return atbl_rec
            else:
                raise RuntimeError("there was a problem saving that record")
        except requests.exceptions.HTTPError as exc:
            #logger.exception(exc, stack_info=True)
            # pprint(exc.response.__dict__)
            _content = exc.response.__dict__['_content']
            content = _content.decode('utf-8')
            error_response = json.loads(content)
            # pprint(error_response['error'])
            if error_response['error']['type'] == 'INVALID_MULTIPLE_CHOICE_OPTIONS':
                try:
                    match = re.search('""(.*?)""', error_response['error']['message'])
                    if match:
                        problem_value = match.group(1)
                except:
                    problem_value = error_response['error']['message']
                logger.warning("A multiple choice option in the local record "
                                 "does not exist in the destination field. \n"
                                 "Please review the option below and either: \n"
                                 "1. modify it in the source record to match an existing value \n"
                                 "2. add it to the list of values in that Airtable field")
                logger.warning(f"problem value: {problem_value}")
                input("Press any key to exit")
                exit()
            else:
                logger.exception(exc, stack_info=True)
                raise RuntimeError("there was a problem saving that record")

    def send(self) -> Self:
        '''
        primary means of updating / inserting

        looks up value of primary field in Airtable
        if found, updates record
        if not found, creates a new record
        '''
        logger.info("sending local record to Airtable...")
        primary_field_name, self_primary_field_value = self._get_primary_key_info()
        logger.debug(f"searching for existing record, with:\
                    \nprimary_key = {primary_field_name}\
                    \nfield_value{self_primary_field_value}")
        # atbl_rec_remote here is not Model object
        atbl_rec_remote = self._search_on_primary_field(
                            primary_field_name, self_primary_field_value)
        if atbl_rec_remote:
            atbl_rec_remote = self._fill_remote_rec_from_local(atbl_rec_remote)
        else:
            atbl_rec_remote = self
        atbl_rec_remote = self._save_rec(atbl_rec_remote)
        return atbl_rec_remote


class THMHashRecord(Model, THMAirtableRecord):
    '''
    object class for Physical Assets at AVMPI
    '''
    field_map = get_field_map('HashRecord')
    '''
    add every key in the field map as an attribute to the class
    each attribute is an Airtable field with a type
    '''
    for field, mapping in field_map.items():
        try:
            field_type = mapping['atbl']['type']
            field_name = mapping['atbl']['name']
            if field_type == 'integer':
                vars()[field] = fields.IntegerField(field_name)
        except (KeyError, TypeError) as exc:
            vars()[field] = fields.TextField(mapping['atbl'])
    
        class Meta:
            base_id = "appNqyF9ABHwSD9si"
            table_name = "Hashes"
            typecast = False

            @staticmethod
            def api_key():
                return get_api_key()

    def from_filemaker(self, row: dict) -> dict:
        '''
        creates an Airtable record from a row in an Excel file
        using field mapping
        '''
        return super().from_filemaker(row, self.field_map)