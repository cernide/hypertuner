# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import six
import warnings

from hestia.list_utils import to_list
from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from polyaxon_schemas.base import BaseConfig, BaseSchema
from polyaxon_schemas.fields import DictOrStr
from polyaxon_schemas.ops.environments.outputs import OutputsSchema
from polyaxon_schemas.ops.environments.persistence import PersistenceSchema
from polyaxon_schemas.ops.environments.resources import (
    K8SContainerResourcesConfig,
    PodResourcesConfig
)


class StoreRefSchema(Schema):
    name = fields.Str()
    init = fields.Bool(allow_none=True)
    paths = fields.List(fields.Str(), allow_none=True)


class K8SResourceRefSchema(Schema):
    name = fields.Str()
    mount_path = fields.Str(allow_none=True)
    items = fields.List(fields.Str(), allow_none=True)


def validate_configmap_refs(values):
    if values.get('config_map_refs') and values.get('configmap_refs'):
        raise ValidationError('You should only use `config_map_refs`.')

    if values.get('configmap_refs'):
        warnings.warn(
            'The `configmap_refs` parameter is deprecated and will be removed in next release, '
            'please use `config_map_refs` instead.',
            DeprecationWarning)
        values['config_map_refs'] = values.pop('configmap_refs')

    return values


def validate_resource_refs(values):
    validate_configmap_refs(values)

    def validate_field(field):
        field_value = values.get(field)
        if not field_value:
            return field_value
        field_value = [{'name': v} if isinstance(v, six.string_types) else v
                       for v in field_value]
        for v in field_value:
            try:
                K8SResourceRefSchema(unknown=BaseConfig.UNKNOWN_BEHAVIOUR).load(v)
            except ValidationError:
                raise ValidationError('K8S Resource field `{}` is not value.'.format(v))
        return field_value

    values['config_map_refs'] = validate_field('config_map_refs')
    values['secret_refs'] = validate_field('secret_refs')
    return values


def validate_persistence(values, is_schema=False):
    if values.get('persistence') and (values.get('data_refs') or
                                      values.get('artifact_refs')):
        raise ValidationError('You cannot use `persistence` and  `data_refs` or `artifact_refs`.')

    if values.get('persistence') and is_schema:
        warnings.warn(
            'The `persistence` parameter is deprecated and will be removed in next release, '
            'please use `data_refs` and/or `artifact_refs` instead.',
            DeprecationWarning)
        persistence = values.pop('persistence')
        values['data_refs'] = values.get('data_refs', persistence.data)
        values['artifact_refs'] = to_list(values.get('artifact_refs', persistence.outputs),
                                          check_none=True)

    def validate_field(field):
        field_value = values.get(field)
        if not field_value:
            return field_value
        field_value = [{'name': v, 'init': True} if isinstance(v, six.string_types) else v
                       for v in field_value]
        for v in field_value:
            try:
                StoreRefSchema(unknown=BaseConfig.UNKNOWN_BEHAVIOUR).load(v)
            except ValidationError:
                raise ValidationError('Persistence field `{}` is not value.'.format(v))
        return field_value

    values['data_refs'] = validate_field('data_refs')
    values['artifact_refs'] = validate_field('artifact_refs')
    return values


def validate_outputs(values, is_schema=False):
    if values.get('outputs'):
        warnings.warn(
            'The `outputs` parameter is deprecated and will be removed in next release, '
            'please notice that it will be ignored.',
            DeprecationWarning)
        if is_schema:
            values.pop('outputs')


def validate_resources(values):
    resources = values.pop('resources', None)
    if not resources:
        return values

    try:  # Check deprecated resources
        resources = PodResourcesConfig.from_dict(resources)
        warnings.warn(
            'The `resources` parameter should specify a k8s compliant format.',
            DeprecationWarning)
        values['resources'] = K8SContainerResourcesConfig.from_resources_entry(resources)
    except ValidationError:
        values['resources'] = resources

    return values


class EnvironmentSchema(BaseSchema):
    # To indicate which worker/ps index this session config belongs to
    index = fields.Int(allow_none=True)
    resources = fields.Dict(allow_none=True)
    labels = fields.Dict(allow_none=True)
    annotations = fields.Dict(allow_none=True)
    node_selector = fields.Dict(allow_none=True)
    affinity = fields.Dict(allow_none=True)
    tolerations = fields.List(fields.Dict(), allow_none=True)
    service_account = fields.Str(allow_none=True)
    image_pull_secrets = fields.List(fields.Str(), allow_none=True)
    max_restarts = fields.Int(allow_none=True)  # Deprecated
    max_retries = fields.Int(allow_none=True)
    restart_policy = fields.Str(allow_none=True)
    ttl = fields.Int(allow_none=True)
    timeout = fields.Int(allow_none=True)
    env_vars = fields.List(fields.List(fields.Raw(), validate=validate.Length(equal=2)),
                           allow_none=True)
    secret_refs = fields.List(DictOrStr(), allow_none=True)
    config_map_refs = fields.List(DictOrStr(), allow_none=True)
    configmap_refs = fields.List(fields.Str(), allow_none=True)  # Deprecated
    data_refs = fields.List(DictOrStr(), allow_none=True)
    artifact_refs = fields.List(DictOrStr(), allow_none=True)
    outputs = fields.Nested(OutputsSchema, allow_none=True)  # Deprecated
    persistence = fields.Nested(PersistenceSchema, allow_none=True)  # Deprecated
    security_context = fields.Dict(allow_none=True)

    @staticmethod
    def schema_config():
        return EnvironmentConfig

    @validates_schema
    def validate_configmap_refs(self, values):
        validate_resource_refs(values)

    @validates_schema
    def validate_persistence(self, values):
        validate_persistence(values, is_schema=True)

    @validates_schema
    def validate_resources(self, values):
        validate_resources(values)
    #
    # @validates_schema
    # def validate_outputs(self, values):
    #     validate_outputs(values, is_schema=True)


class EnvironmentConfig(BaseConfig):
    """
    Pod environment config.

    Args:
        index: `int | None`. The index of the pod.
        resources: `PodResourcesConfig`.
        node_selector: `dict`.
        affinity: `dict`.
        tolerations: `list(dict)`.
    """
    IDENTIFIER = 'environment'
    SCHEMA = EnvironmentSchema
    REDUCED_ATTRIBUTES = ['index',
                          'resources',
                          'labels',
                          'annotations',
                          'node_selector',
                          'affinity',
                          'tolerations',
                          'service_account',
                          'image_pull_secrets',
                          'max_retries',
                          'timeout',
                          'restart_policy',
                          'ttl',
                          'env_vars',
                          'secret_refs',
                          'config_map_refs',
                          'data_refs',
                          'artifact_refs',
                          'outputs',
                          'security_context']

    def __init__(self,
                 index=None,
                 resources=None,
                 labels=None,
                 annotations=None,
                 node_selector=None,
                 affinity=None,
                 tolerations=None,
                 service_account=None,
                 image_pull_secrets=None,
                 max_restarts=None,
                 max_retries=None,
                 timeout=None,
                 restart_policy=None,
                 ttl=None,
                 env_vars=None,
                 secret_refs=None,
                 config_map_refs=None,
                 configmap_refs=None,
                 data_refs=None,
                 artifact_refs=None,
                 persistence=None,
                 outputs=None,
                 security_context=None,
                 ):
        if max_restarts:
            warnings.warn(
                'The `max_restarts` is deprecated and has no effect, please use `max_retries`.',
                DeprecationWarning)
        self.index = index
        self.resources = validate_resources({'resources': resources}).get('resources')
        self.labels = labels
        self.annotations = annotations
        self.node_selector = node_selector
        self.affinity = affinity
        self.tolerations = tolerations
        self.service_account = service_account
        self.image_pull_secrets = image_pull_secrets
        self.max_retries = max_retries
        self.timeout = timeout
        self.restart_policy = restart_policy
        self.ttl = ttl
        self.env_vars = env_vars

        resource_refs = validate_resource_refs({
            'config_map_refs': config_map_refs,
            'configmap_refs': configmap_refs,
            'secret_refs': secret_refs
        })
        self.secret_refs = resource_refs.get('secret_refs')
        self.config_map_refs = resource_refs.get('config_map_refs')

        persistence_values = validate_persistence({
            'persistence': persistence,
            'data_refs': data_refs,
            'artifact_refs': artifact_refs
        })
        self.data_refs = persistence_values.get('data_refs')
        self.artifact_refs = persistence_values.get('artifact_refs')
        # validate_outputs({'outputs': outputs})
        self.outputs = outputs
        self.security_context = security_context
