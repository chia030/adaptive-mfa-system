<!-- src/Login.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  
  let username = "";
  let password = "";
  
  function handleSubmit(event) {
    event.preventDefault();
    // Dispatch a login event with credentials
    dispatch('login', { username, password });
  }
</script>

<form on:submit={handleSubmit}>
  <div>
    <label for="username">Username:</label>
    <input id="username" type="text" bind:value={username} required />
  </div>
  <div>
    <label for="password">Password:</label>
    <input id="password" type="password" bind:value={password} required />
  </div>
  <button type="submit">Login</button>
</form>
