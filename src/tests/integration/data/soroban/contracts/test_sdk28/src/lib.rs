#![no_std]

use soroban_sdk::xdr::{FromXdr, ToXdr};
use soroban_sdk::{contract, contractimpl, contracttype, symbol_short, Env, String};

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Record {
    pub amount: i128,
    pub label: String,
    pub optional: Option<u32>,
}

#[contract]
pub struct TestSdk28;

#[contractimpl]
impl TestSdk28 {
    pub fn test_roundtrip(env: Env, amount: u32) -> bool {
        let record = Record {
            amount: amount.into(),
            label: String::from_str(&env, "sdk28"),
            optional: None,
        };
        let key = symbol_short!("record");
        env.storage().instance().set(&key, &record);
        let stored: Record = env.storage().instance().get(&key).unwrap();
        let encoded = stored.clone().to_xdr(&env);
        let decoded = Record::from_xdr(&env, &encoded).unwrap();
        let mut label = [0; 5];
        decoded.label.copy_into_slice(&mut label);
        stored == record && decoded == record && decoded.label.len() == 5 && label == *b"sdk28"
    }
}
