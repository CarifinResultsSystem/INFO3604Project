<template>
    <div class="users">
        <h1>Users</h1>
        <ul>
            <li v-for="user in users" :key="user.id">
                {{ user.username }} - {{ user.id }}
            </li>
        </ul>
    </div>
</template>

<script>
import axios from 'axios';

export default{
    name: 'Users',
    data(){
        return{
            users: [],
        };
    },
    methods: {
        getMessage(){
            const path = 'http://localhost:5000/users';
            axios.get(path)
                .then((res) => {
                    this.users = res.data;
                })
                .catch((error) => {
                    console.error(error);
                });
        }
    },
    created(){
        this.getMessage();
    },
};
</script>