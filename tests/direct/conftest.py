import importlib
import sys

import pytest


def _import_first(*module_names):
    for module_name in module_names:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
    raise ImportError(f"None of these GenLayer modules exist: {module_names}")


def _install_genvm_0216_compatibility():
    """Bridge genlayer-test 0.29's 0.3 imports to the stable 0.2.16 SDK."""
    from gltest.direct import loader, sdk_compat, wasi_mock

    sdk_compat.import_calldata = lambda: _import_first(
        "genlayer.calldata", "genlayer.py.calldata"
    )
    sdk_compat.import_types = lambda: _import_first(
        "genlayer.types", "genlayer.py.types"
    )
    loader.import_calldata = sdk_compat.import_calldata
    loader.import_address = sdk_compat.import_address
    loader.import_lazy = sdk_compat.import_lazy

    wasi_mock.import_calldata = sdk_compat.import_calldata

    def allocate_with_legacy_storage(contract_cls, vm, *args, **kwargs):
        storage = importlib.import_module("genlayer.py.storage")
        generate = importlib.import_module(
            "genlayer.py.storage._internal.generate"
        )
        storage.Root.MANAGER = vm._storage
        description = generate._storage_build(contract_cls, {})
        slot = vm._storage.get_store_slot(storage.ROOT_SLOT_ID)
        instance = description.get(slot, 0)
        init = getattr(description, "cls", None)
        init = getattr(init, "__init__", None) if init else contract_cls.__init__
        if hasattr(init, generate.ORIGINAL_INIT_ATTR):
            init = getattr(init, generate.ORIGINAL_INIT_ATTR)
        init(instance, *args, **kwargs)

        gl_vm = importlib.import_module("genlayer.gl.vm")
        sys.modules["genlayer.vm"] = gl_vm

        def run_nondet_unsafe(leader_fn, validator_fn, /, **_kwargs):
            from gltest.direct import wasi_mock

            active_vm = wasi_mock.get_vm()
            if active_vm._check_pickling:
                loader._validate_pickling(leader_fn, "leader_fn")
                loader._validate_pickling(validator_fn, "validator_fn")
            active_vm._in_nondet = True
            try:
                result = leader_fn()
            finally:
                active_vm._in_nondet = False
            active_vm._captured_validators.append(
                (result, leader_fn, validator_fn)
            )
            if validator_fn(gl_vm.Return(calldata=result)) is not True:
                raise gl_vm.UserError("CONSENSUS_REJECTED")
            return result

        gl_vm.run_nondet_unsafe = run_nondet_unsafe
        return instance

    loader._allocate_contract = allocate_with_legacy_storage


_install_genvm_0216_compatibility()


@pytest.fixture(autouse=True)
def enable_pickling_checks(direct_vm):
    direct_vm.check_pickling = True
